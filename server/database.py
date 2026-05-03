import aiosqlite
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "agent_pilot.db")


async def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            status TEXT DEFAULT 'online'
        );

        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            type TEXT DEFAULT 'private',
            name TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id TEXT,
            user_id TEXT,
            PRIMARY KEY (chat_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            sender_id TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            reply_to_id TEXT,
            card_data TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            recalled_at TEXT,
            FOREIGN KEY (chat_id) REFERENCES chats(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            outline TEXT DEFAULT '[]',
            status TEXT DEFAULT 'draft',
            task_id TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS presentations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            slides TEXT DEFAULT '[]',
            template TEXT DEFAULT 'default',
            source_doc_id TEXT,
            task_id TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            chat_id TEXT,
            user_id TEXT,
            intent TEXT,
            plan TEXT DEFAULT '[]',
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            result TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    await _seed_data(db)
    await db.commit()
    await db.close()


async def _seed_data(db):
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    if row[0] > 0:
        return

    users = [
        ("alice", "Alice", "", "online"),
        ("bob", "Bob", "", "online"),
        ("charlie", "Charlie", "", "busy"),
        ("diana", "Diana", "", "online"),
        ("agent", "Agent-Pilot", "", "online"),
    ]
    await db.executemany(
        "INSERT INTO users (id, name, avatar, status) VALUES (?, ?, ?, ?)", users
    )

    chats = [
        ("chat_alice_agent", "private", "Agent-Pilot"),
        ("chat_alice_bob", "private", "Bob"),
        ("chat_alice_charlie", "private", "Charlie"),
        ("chat_alice_diana", "private", "Diana"),
        ("chat_group_team", "group", "产品团队"),
    ]
    await db.executemany(
        "INSERT INTO chats (id, type, name) VALUES (?, ?, ?)", chats
    )

    members = [
        ("chat_alice_agent", "alice"), ("chat_alice_agent", "agent"),
        ("chat_alice_bob", "alice"), ("chat_alice_bob", "bob"),
        ("chat_alice_charlie", "alice"), ("chat_alice_charlie", "charlie"),
        ("chat_alice_diana", "alice"), ("chat_alice_diana", "diana"),
        ("chat_group_team", "alice"), ("chat_group_team", "bob"),
        ("chat_group_team", "charlie"), ("chat_group_team", "diana"),
        ("chat_group_team", "agent"),
    ]
    await db.executemany(
        "INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?, ?)"
        if False else "INSERT INTO chat_members (chat_id, user_id) VALUES (?, ?)",
        members,
    )

    now = datetime.utcnow().isoformat()
    seed_messages = [
        ("msg_seed_1", "chat_alice_bob", "bob", "今天版本我已经看过了，聊天主流程没有问题。", "text", now),
        ("msg_seed_2", "chat_alice_bob", "alice", "好，我等下把输入区和会话列表再 polish 一下。", "text", now),
        ("msg_seed_3", "chat_alice_charlie", "charlie", "明早我们可以一起过一下演示流程。", "text", now),
        ("msg_seed_4", "chat_alice_diana", "diana", "UI 这版已经比之前更像 IM 了。", "text", now),
        ("msg_seed_5", "chat_alice_agent", "agent", "你好！我是 Agent-Pilot，你的 AI 协同助手。\n\n你可以在这里给我发指令，比如：\n- \"帮我写一份产品方案\"\n- \"把上次讨论整理成文档\"\n- \"做一个10页的项目汇报PPT\"\n\n有什么我可以帮你的？", "text", now),
    ]
    await db.executemany(
        "INSERT INTO messages (id, chat_id, sender_id, content, msg_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        seed_messages,
    )
