import asyncio
import sys
sys.path.insert(0, ".")

from database import get_db, init_db
from routes_auth import hash_password, verify_password

async def test():
    await init_db()
    db = await get_db()
    cursor = await db.execute("SELECT id, name, password_hash FROM users WHERE id = ?", ("alice",))
    row = await cursor.fetchone()
    await db.close()

    if not row:
        print("ERROR: alice not found")
        return

    r = dict(row)
    print(f"User: {r['id']}, name: {r['name']}, pw_hash_len: {len(r.get('password_hash', ''))}")

    # Simulate login flow
    pw_hash = r.get("password_hash", "")
    if not pw_hash:
        print("No password set, setting now...")
        new_hash = hash_password("test1234")
        db = await get_db()
        await db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, "alice"))
        await db.commit()
        await db.close()
        print(f"Password set: {new_hash[:30]}...")
    else:
        ok = verify_password("test1234", pw_hash)
        print(f"Password verify: {ok}")

    # Test login via httpx
    from httpx import AsyncClient, ASGITransport
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"username": "alice", "password": "test1234"})
        print(f"Login status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
        else:
            data = resp.json()
            print(f"Token: {data['token'][:20]}...")

asyncio.run(test())
