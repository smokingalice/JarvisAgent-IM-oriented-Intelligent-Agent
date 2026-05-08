import asyncio
import sys
sys.path.insert(0, ".")

from httpx import AsyncClient, ASGITransport
from main import app


async def test_all():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login to get token
        resp = await client.post("/api/auth/login", json={"username": "alice", "password": "test1234"})
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[PASS] Auth login")

        # 2. Test documents list
        resp = await client.get("/api/documents", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] GET /documents -> {resp.status_code}")

        # 3. Test presentations list
        resp = await client.get("/api/presentations", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] GET /presentations -> {resp.status_code}")

        # 4. Test friends list
        resp = await client.get("/api/friends", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] GET /friends -> {resp.status_code}")

        # 5. Test multi-device sessions
        resp = await client.get("/api/sessions", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] GET /sessions -> {resp.status_code}")
        if resp.status_code == 200:
            print(f"       Sessions: {resp.json()}")

        # 6. Test agent chat endpoint
        resp = await client.post("/api/agent/chat", json={"chat_id": "test_chat", "message": "你好", "user_id": "alice"}, headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] POST /agent/chat -> {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"       Task ID: {data.get('task_id', 'N/A')}, Status: {data.get('status', 'N/A')}")

        # 7. Test document export
        resp = await client.get("/api/documents", headers=headers)
        docs = resp.json()
        if docs:
            doc_id = docs[0]["id"]
            resp = await client.get(f"/api/documents/{doc_id}/export?format=md", headers=headers)
            status = "PASS" if resp.status_code == 200 else "FAIL"
            print(f"[{status}] GET /documents/{{id}}/export -> {resp.status_code}")
        else:
            print("[SKIP] No documents to test export")

        # 8. Test auth/me
        resp = await client.get("/api/auth/me", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] GET /auth/me -> {resp.status_code}")

        # 9. Test logout
        resp = await client.post("/api/auth/logout", headers=headers)
        status = "PASS" if resp.status_code == 200 else "FAIL"
        print(f"[{status}] POST /auth/logout -> {resp.status_code}")

        # 10. Verify token is invalid after logout
        resp = await client.get("/api/friends", headers=headers)
        status = "PASS" if resp.status_code == 401 else "FAIL"
        print(f"[{status}] Token invalidated after logout -> {resp.status_code}")

    print("\n--- All tests completed ---")


asyncio.run(test_all())
