import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from database import get_db
from routes_auth import get_current_user
from ws_manager import manager

router = APIRouter(tags=["Friends"])


@router.get("/friends")
async def list_friends(user_id: str = Depends(get_current_user)):
    db = await get_db()
    cursor = await db.execute("""
        SELECT u.id, u.name, u.avatar, u.status, f.created_at as friendship_since
        FROM friendships f
        JOIN users u ON (
            CASE WHEN f.from_user_id = %s THEN f.to_user_id ELSE f.from_user_id END
        ) = u.id
        WHERE (f.from_user_id = %s OR f.to_user_id = %s) AND f.status = 'accepted'
    """, (user_id, user_id, user_id))
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]


@router.get("/friends/requests")
async def list_friend_requests(user_id: str = Depends(get_current_user)):
    db = await get_db()
    cursor = await db.execute("""
        SELECT f.id, f.from_user_id, u.name as from_name, f.created_at
        FROM friendships f
        JOIN users u ON f.from_user_id = u.id
        WHERE f.to_user_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """, (user_id,))
    incoming = [dict(row) for row in await cursor.fetchall()]

    cursor = await db.execute("""
        SELECT f.id, f.to_user_id, u.name as to_name, f.created_at
        FROM friendships f
        JOIN users u ON f.to_user_id = u.id
        WHERE f.from_user_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """, (user_id,))
    outgoing = [dict(row) for row in await cursor.fetchall()]

    await db.close()
    return {"incoming": incoming, "outgoing": outgoing}


@router.post("/friends/request")
async def send_friend_request(target_user_id: str = Query(default=None), user_id: str = Depends(get_current_user)):
    if target_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
    if target_user_id == "agent":
        raise HTTPException(status_code=400, detail="Cannot add Agent as friend")

    db = await get_db()

    cursor = await db.execute("SELECT id FROM users WHERE id = %s", (target_user_id,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor = await db.execute("""
        SELECT id, status FROM friendships
        WHERE (from_user_id = %s AND to_user_id = %s) OR (from_user_id = %s AND to_user_id = %s)
    """, (user_id, target_user_id, target_user_id, user_id))
    existing = await cursor.fetchone()
    if existing:
        if existing["status"] == "accepted":
            await db.close()
            raise HTTPException(status_code=409, detail="Already friends")
        if existing["status"] == "pending":
            await db.close()
            raise HTTPException(status_code=409, detail="Friend request already pending")

    friendship_id = f"fr_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "INSERT INTO friendships (id, from_user_id, to_user_id, status, created_at, updated_at) VALUES (%s, %s, %s, 'pending', %s, %s)",
        (friendship_id, user_id, target_user_id, now, now)
    )
    await db.commit()
    await db.close()

    await manager.broadcast_to_user(target_user_id, {
        "type": "friend_request",
        "data": {"id": friendship_id, "from_user_id": user_id, "created_at": now}
    })

    return {"id": friendship_id, "status": "pending"}


@router.post("/friends/accept/{friendship_id}")
async def accept_friend_request(friendship_id: str, user_id: str = Depends(get_current_user)):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM friendships WHERE id = %s AND to_user_id = %s AND status = 'pending'",
        (friendship_id, user_id)
    )
    row = await cursor.fetchone()
    if not row:
        await db.close()
        raise HTTPException(status_code=404, detail="Friend request not found")

    friendship = dict(row)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "UPDATE friendships SET status = 'accepted', updated_at = %s WHERE id = %s",
        (now, friendship_id)
    )

    from_user = friendship["from_user_id"]
    chat_id = f"chat_{min(user_id, from_user)}_{max(user_id, from_user)}"

    cursor = await db.execute("SELECT name FROM users WHERE id = %s", (from_user,))
    friend_row = await cursor.fetchone()
    friend_name = friend_row["name"] if friend_row else from_user

    cursor = await db.execute("SELECT name FROM users WHERE id = %s", (user_id,))
    my_row = await cursor.fetchone()
    my_name = my_row["name"] if my_row else user_id

    await db.execute(
        "INSERT IGNORE INTO chats (id, type, name) VALUES (%s, 'private', %s)",
        (chat_id, friend_name)
    )
    await db.execute(
        "INSERT IGNORE INTO chat_members (chat_id, user_id) VALUES (%s, %s)",
        (chat_id, user_id)
    )
    await db.execute(
        "INSERT IGNORE INTO chat_members (chat_id, user_id) VALUES (%s, %s)",
        (chat_id, from_user)
    )

    await db.commit()
    await db.close()

    await manager.broadcast_to_user(from_user, {
        "type": "friend_accepted",
        "data": {"friendship_id": friendship_id, "user_id": user_id, "user_name": my_name, "chat_id": chat_id}
    })

    return {"status": "accepted", "chat_id": chat_id}


@router.post("/friends/reject/{friendship_id}")
async def reject_friend_request(friendship_id: str, user_id: str = Depends(get_current_user)):
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM friendships WHERE id = %s AND to_user_id = %s AND status = 'pending'",
        (friendship_id, user_id)
    )
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Friend request not found")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "UPDATE friendships SET status = 'rejected', updated_at = %s WHERE id = %s",
        (now, friendship_id)
    )
    await db.commit()
    await db.close()
    return {"status": "rejected"}


@router.get("/users/search")
async def search_users(q: str, user_id: str = Depends(get_current_user)):
    if not q or len(q) < 1:
        return []
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, name, avatar, status FROM users WHERE (id LIKE %s OR name LIKE %s) AND id != %s AND id != 'agent' LIMIT 20",
        (f"%{q}%", f"%{q}%", user_id)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(row) for row in rows]
