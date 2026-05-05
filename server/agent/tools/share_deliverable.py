import uuid
from datetime import datetime
from database import get_db
from ws_manager import manager


async def share_deliverable_tool(params: dict, chat_id: str = "") -> dict:
    resource_id = params.get("resource_id") or params.get("resourceId", "")
    resource_type = params.get("resource_type") or params.get("resourceType", "document")
    share_to = params.get("share_to") or params.get("shareTo", "current_chat")

    if not resource_id:
        return {"message": "没有指定要分享的资源"}

    db = await get_db()
    if resource_type == "document":
        cursor = await db.execute("SELECT id, title FROM documents WHERE id = %s", (resource_id,))
    else:
        cursor = await db.execute("SELECT id, title FROM presentations WHERE id = %s", (resource_id,))
    row = await cursor.fetchone()
    await db.close()

    if not row:
        return {"message": f"资源不存在: {resource_id}"}

    resource = dict(row)
    share_id = f"share_{uuid.uuid4().hex[:8]}"
    share_link = f"/shared/{share_id}"

    icon = "📄" if resource_type == "document" else "📊"
    message = f"{icon} **{resource['title']}** 已分享\n\n查看链接: {share_link}"

    return {
        "share_id": share_id,
        "share_link": share_link,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "message": message,
    }
