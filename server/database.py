import aiomysql
import json
from datetime import datetime
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DATABASE,
            charset="utf8mb4",
            autocommit=False,
            minsize=2,
            maxsize=10,
        )
    return _pool


async def get_db():
    pool = await get_pool()
    conn = await pool.acquire()
    return DBConnection(pool, conn)


class DBConnection:
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._cursor = None

    async def execute(self, sql, params=None):
        self._cursor = await self._conn.cursor(aiomysql.DictCursor)
        await self._cursor.execute(sql, params)
        return self._cursor

    async def executemany(self, sql, params_list):
        self._cursor = await self._conn.cursor(aiomysql.DictCursor)
        await self._cursor.executemany(sql, params_list)
        return self._cursor

    async def commit(self):
        await self._conn.commit()

    async def close(self):
        self._pool.release(self._conn)


async def init_db():
    db = await get_db()

    tables = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            avatar TEXT,
            status VARCHAR(50) DEFAULT 'online',
            password_hash TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS friendships (
            id VARCHAR(255) PRIMARY KEY,
            from_user_id VARCHAR(255) NOT NULL,
            to_user_id VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (from_user_id) REFERENCES users(id),
            FOREIGN KEY (to_user_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS chats (
            id VARCHAR(255) PRIMARY KEY,
            type VARCHAR(50) DEFAULT 'private',
            name VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id VARCHAR(255),
            user_id VARCHAR(255),
            PRIMARY KEY (chat_id, user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(255) PRIMARY KEY,
            chat_id VARCHAR(255) NOT NULL,
            sender_id VARCHAR(255) NOT NULL,
            content LONGTEXT NOT NULL,
            msg_type VARCHAR(50) DEFAULT 'text',
            reply_to_id VARCHAR(255),
            card_data LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            recalled_at DATETIME,
            FOREIGN KEY (chat_id) REFERENCES chats(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS documents (
            id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            content LONGTEXT,
            outline LONGTEXT,
            status VARCHAR(50) DEFAULT 'draft',
            task_id VARCHAR(255),
            created_by VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS presentations (
            id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            slides LONGTEXT,
            template VARCHAR(255) DEFAULT 'default',
            source_doc_id VARCHAR(255),
            task_id VARCHAR(255),
            created_by VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR(255) PRIMARY KEY,
            chat_id VARCHAR(255),
            user_id VARCHAR(255),
            intent TEXT,
            plan LONGTEXT,
            status VARCHAR(50) DEFAULT 'pending',
            progress INT DEFAULT 0,
            result LONGTEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    for sql in tables:
        await db.execute(sql)

    await _seed_data(db)
    await db.commit()
    await db.close()


async def _seed_data(db):
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
    row = await cursor.fetchone()
    if row["cnt"] > 0:
        return

    users = [
        ("alice", "Alice", "", "online"),
        ("bob", "Bob", "", "online"),
        ("charlie", "Charlie", "", "busy"),
        ("diana", "Diana", "", "online"),
        ("agent", "JarvisAgent", "", "online"),
    ]
    await db.executemany(
        "INSERT INTO users (id, name, avatar, status) VALUES (%s, %s, %s, %s)", users
    )

    chats = [
        ("chat_alice_agent", "private", "JarvisAgent"),
        ("chat_alice_bob", "private", "Bob"),
        ("chat_alice_charlie", "private", "Charlie"),
        ("chat_alice_diana", "private", "Diana"),
        ("chat_group_team", "group", "产品团队"),
    ]
    await db.executemany(
        "INSERT INTO chats (id, type, name) VALUES (%s, %s, %s)", chats
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
        "INSERT INTO chat_members (chat_id, user_id) VALUES (%s, %s)", members
    )

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    seed_messages = [
        ("msg_seed_1", "chat_alice_bob", "bob", "今天版本我已经看过了，聊天主流程没有问题。", "text", now),
        ("msg_seed_2", "chat_alice_bob", "alice", "好，我等下把输入区和会话列表再 polish 一下。", "text", now),
        ("msg_seed_3", "chat_alice_charlie", "charlie", "明早我们可以一起过一下演示流程。", "text", now),
        ("msg_seed_4", "chat_alice_diana", "diana", "UI 这版已经比之前更像 IM 了。", "text", now),
        ("msg_seed_5", "chat_alice_agent", "agent", "你好！我是 JarvisAgent，你的 AI 协同助手。\n\n你可以在这里给我发指令，比如：\n- \"帮我写一份产品方案\"\n- \"把上次讨论整理成文档\"\n- \"做一个10页的项目汇报PPT\"\n\n有什么我可以帮你的？", "text", now),
    ]
    await db.executemany(
        "INSERT INTO messages (id, chat_id, sender_id, content, msg_type, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        seed_messages,
    )
