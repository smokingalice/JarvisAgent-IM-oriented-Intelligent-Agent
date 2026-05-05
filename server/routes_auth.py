import uuid
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from jose import jwt, JWTError
import bcrypt
from database import get_db
from config import JWT_SECRET, JWT_EXPIRE_HOURS

router = APIRouter(tags=["Auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


class RegisterRequest(BaseModel):
    username: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: str = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    return verify_token(token)


@router.post("/auth/register")
async def register(req: RegisterRequest):
    if not req.username or len(req.username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    db = await get_db()
    cursor = await db.execute("SELECT id FROM users WHERE id = ?", (req.username,))
    existing = await cursor.fetchone()
    if existing:
        await db.close()
        raise HTTPException(status_code=409, detail="Username already exists")

    password_hash = hash_password(req.password)
    name = req.name or req.username
    now = datetime.utcnow().isoformat()

    await db.execute(
        "INSERT INTO users (id, name, avatar, status, password_hash, created_at) VALUES (?, ?, '', 'online', ?, ?)",
        (req.username, name, password_hash, now)
    )

    # Auto-create a chat with JarvisAgent for the new user
    chat_id = f"chat_{req.username}_agent"
    await db.execute(
        "INSERT OR IGNORE INTO chats (id, type, name) VALUES (?, 'private', 'JarvisAgent')",
        (chat_id,)
    )
    await db.execute(
        "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, ?)",
        (chat_id, req.username)
    )
    await db.execute(
        "INSERT OR IGNORE INTO chat_members (chat_id, user_id) VALUES (?, 'agent')",
        (chat_id,)
    )

    # Send welcome message from agent
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    await db.execute(
        "INSERT INTO messages (id, chat_id, sender_id, content, msg_type, created_at) VALUES (?, ?, 'agent', ?, 'text', ?)",
        (msg_id, chat_id, f"你好 {name}！我是 JarvisAgent，你的 AI 协同助手。\n\n你可以给我发指令，比如：\n- \"帮我写一份产品方案\"\n- \"把讨论整理成文档\"\n- \"做一个10页的PPT\"\n\n有什么我可以帮你的？", now)
    )

    await db.commit()
    await db.close()

    token = create_token(req.username)
    return {
        "token": token,
        "user": {"id": req.username, "name": name, "avatar": "", "status": "online"}
    }


@router.post("/auth/login")
async def login(req: LoginRequest):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (req.username,))
    row = await cursor.fetchone()
    await db.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user = dict(row)
    password_hash = user.get("password_hash", "")

    # For seed users without passwords, allow login with any password on first attempt and set it
    if not password_hash:
        db = await get_db()
        new_hash = hash_password(req.password)
        await db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, req.username))
        await db.commit()
        await db.close()
    else:
        if not verify_password(req.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(req.username)
    return {
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "avatar": user.get("avatar", ""), "status": user.get("status", "online")}
    }


@router.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    db = await get_db()
    cursor = await db.execute("SELECT id, name, avatar, status FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)
