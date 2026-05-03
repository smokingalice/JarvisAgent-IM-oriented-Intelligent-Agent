import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from database import get_db
from models import SendMessageRequest, Message
from ws_manager import manager

router = APIRouter(tags=["IM"])


@router.get("/users")
async def get_users():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/chats")
async def get_chats(user_id: str = "alice"):
    db = await get_db()
    cursor = await db.execute("""
        SELECT c.id, c.type, c.name, c.created_at
        FROM chats c
        JOIN chat_members cm ON c.id = cm.chat_id
        WHERE cm.user_id = ?
    """, (user_id,))
    chats = [dict(row) for row in await cursor.fetchall()]

    for chat in chats:
        msg_cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = ? AND recalled_at IS NULL
            ORDER BY created_at DESC LIMIT 1
        """, (chat["id"],))
        last_msg = await msg_cursor.fetchone()
        chat["last_message"] = dict(last_msg) if last_msg else None

        count_cursor = await db.execute("""
            SELECT COUNT(*) as cnt FROM messages
            WHERE chat_id = ? AND sender_id != ? AND recalled_at IS NULL
        """, (chat["id"], user_id))
        count_row = await count_cursor.fetchone()
        chat["unread_count"] = count_row[0] if count_row else 0

    chats.sort(key=lambda c: c["last_message"]["created_at"] if c["last_message"] else "", reverse=True)
    await db.close()
    return chats


@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 50, before: str = None):
    db = await get_db()
    if before:
        cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = ? AND recalled_at IS NULL AND created_at < ?
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, before, limit))
    else:
        cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = ? AND recalled_at IS NULL
            ORDER BY created_at DESC LIMIT ?
        """, (chat_id, limit))
    rows = await cursor.fetchall()
    await db.close()
    messages = [dict(row) for row in rows]
    messages.reverse()
    for msg in messages:
        if msg.get("card_data"):
            try:
                msg["card_data"] = json.loads(msg["card_data"])
            except (json.JSONDecodeError, TypeError):
                pass
    return messages


@router.post("/chats/{chat_id}/messages")
async def send_message(chat_id: str, req: SendMessageRequest, user_id: str = "alice"):
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    db = await get_db()
    await db.execute("""
        INSERT INTO messages (id, chat_id, sender_id, content, msg_type, reply_to_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (msg_id, chat_id, user_id, req.content, req.msg_type, req.reply_to_id, now))
    await db.commit()

    message = {
        "id": msg_id,
        "chat_id": chat_id,
        "sender_id": user_id,
        "content": req.content,
        "msg_type": req.msg_type,
        "reply_to_id": req.reply_to_id,
        "card_data": None,
        "created_at": now,
        "recalled_at": None,
    }

    await manager.broadcast({
        "type": "new_message",
        "data": message,
    }, f"chat:{chat_id}")

    await manager.broadcast({
        "type": "new_message",
        "data": message,
    })

    await db.close()
    return message


@router.delete("/messages/{message_id}")
async def recall_message(message_id: str, user_id: str = "alice"):
    db = await get_db()
    now = datetime.utcnow().isoformat()
    cursor = await db.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    msg = await cursor.fetchone()
    if not msg:
        await db.close()
        raise HTTPException(status_code=404, detail="Message not found")
    if dict(msg)["sender_id"] != user_id:
        await db.close()
        raise HTTPException(status_code=403, detail="Can only recall own messages")

    await db.execute("UPDATE messages SET recalled_at = ? WHERE id = ?", (now, message_id))
    await db.commit()

    await manager.broadcast({
        "type": "message_recalled",
        "data": {"message_id": message_id, "chat_id": dict(msg)["chat_id"]},
    })

    await db.close()
    return {"status": "ok"}
