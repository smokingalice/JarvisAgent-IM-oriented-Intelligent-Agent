import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Query
from database import get_db
from models import SendMessageRequest, Message
from ws_manager import manager
from routes_auth import verify_token

router = APIRouter(tags=["IM"])


def get_user_from_header_or_query(authorization: str = None, user_id: str = None) -> str:
    """Try to extract user from JWT token, fallback to query param."""
    if authorization:
        try:
            token = authorization.replace("Bearer ", "")
            return verify_token(token)
        except Exception:
            pass
    return user_id or "alice"


@router.get("/users")
async def get_users():
    db = await get_db()
    cursor = await db.execute("SELECT id, name, avatar, status FROM users WHERE id != 'agent'")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/chats")
async def get_chats(user_id: str = Query(default=None), authorization: str = Header(default=None)):
    uid = get_user_from_header_or_query(authorization, user_id)
    db = await get_db()
    cursor = await db.execute("""
        SELECT c.id, c.type, c.name, c.created_at
        FROM chats c
        JOIN chat_members cm ON c.id = cm.chat_id
        WHERE cm.user_id = %s
    """, (uid,))
    chats = [dict(row) for row in await cursor.fetchall()]

    for chat in chats:
        if chat["type"] == "private":
            member_cursor = await db.execute("""
                SELECT u.id, u.name FROM chat_members cm
                JOIN users u ON cm.user_id = u.id
                WHERE cm.chat_id = %s AND cm.user_id != %s
            """, (chat["id"], uid))
            other = await member_cursor.fetchone()
            if other:
                chat["display_name"] = other["name"]
            else:
                chat["display_name"] = chat["name"]
        else:
            chat["display_name"] = chat["name"]

        msg_cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = %s AND recalled_at IS NULL
            ORDER BY created_at DESC LIMIT 1
        """, (chat["id"],))
        last_msg = await msg_cursor.fetchone()
        chat["last_message"] = dict(last_msg) if last_msg else None

        count_cursor = await db.execute("""
            SELECT COUNT(*) as cnt FROM messages
            WHERE chat_id = %s AND sender_id != %s AND recalled_at IS NULL
        """, (chat["id"], uid))
        count_row = await count_cursor.fetchone()
        chat["unread_count"] = count_row["cnt"] if count_row else 0

    chats.sort(key=lambda c: c["last_message"]["created_at"] if c["last_message"] else "", reverse=True)
    await db.close()
    return chats


@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: str, limit: int = 50, before: str = None):
    db = await get_db()
    if before:
        cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = %s AND recalled_at IS NULL AND created_at < %s
            ORDER BY created_at DESC LIMIT %s
        """, (chat_id, before, limit))
    else:
        cursor = await db.execute("""
            SELECT * FROM messages
            WHERE chat_id = %s AND recalled_at IS NULL
            ORDER BY created_at DESC LIMIT %s
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


@router.get("/chats/{chat_id}/members")
async def get_chat_members(chat_id: str):
    db = await get_db()
    cursor = await db.execute("""
        SELECT u.id, u.name, u.avatar, u.status
        FROM chat_members cm
        JOIN users u ON cm.user_id = u.id
        WHERE cm.chat_id = %s
    """, (chat_id,))
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.post("/chats/{chat_id}/messages")
async def send_message(chat_id: str, req: SendMessageRequest, user_id: str = Query(default=None), authorization: str = Header(default=None)):
    uid = get_user_from_header_or_query(authorization, user_id)
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    db = await get_db()

    cursor = await db.execute(
        "SELECT 1 FROM chat_members WHERE chat_id = %s AND user_id = %s",
        (chat_id, uid)
    )
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    await db.execute("""
        INSERT INTO messages (id, chat_id, sender_id, content, msg_type, reply_to_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (msg_id, chat_id, uid, req.content, req.msg_type, req.reply_to_id, now))
    await db.commit()

    message = {
        "id": msg_id,
        "chat_id": chat_id,
        "sender_id": uid,
        "content": req.content,
        "msg_type": req.msg_type,
        "reply_to_id": req.reply_to_id,
        "card_data": None,
        "created_at": now,
        "recalled_at": None,
    }

    cursor = await db.execute("SELECT user_id FROM chat_members WHERE chat_id = %s", (chat_id,))
    member_rows = await cursor.fetchall()
    member_ids = [r["user_id"] for r in member_rows]

    await manager.broadcast_to_chat_members(chat_id, {
        "type": "new_message",
        "data": message,
    }, member_ids)

    await db.close()
    return message


@router.delete("/messages/{message_id}")
async def recall_message(message_id: str, user_id: str = Query(default=None), authorization: str = Header(default=None)):
    uid = get_user_from_header_or_query(authorization, user_id)
    db = await get_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    cursor = await db.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
    msg = await cursor.fetchone()
    if not msg:
        await db.close()
        raise HTTPException(status_code=404, detail="Message not found")
    if msg["sender_id"] != uid:
        await db.close()
        raise HTTPException(status_code=403, detail="Can only recall own messages")

    await db.execute("UPDATE messages SET recalled_at = %s WHERE id = %s", (now, message_id))
    await db.commit()

    chat_id = msg["chat_id"]
    cursor = await db.execute("SELECT user_id FROM chat_members WHERE chat_id = %s", (chat_id,))
    member_rows = await cursor.fetchall()
    member_ids = [r["user_id"] for r in member_rows]

    await manager.broadcast_to_chat_members(chat_id, {
        "type": "message_recalled",
        "data": {"message_id": message_id, "chat_id": chat_id},
    }, member_ids)

    await db.close()
    return {"status": "ok"}
