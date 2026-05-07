import json
from datetime import datetime
from openai import AsyncOpenAI
from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL
from database import get_db
from ws_manager import manager

EDIT_SYSTEM_PROMPT = """你是一个专业的文档编辑助手。根据用户的指令修改文档内容。

规则：
1. 输出修改后的完整文档 Markdown
2. 保持文档的整体结构和风格
3. 只修改用户指定的部分
4. 确保修改后的内容连贯自然

只输出修改后的文档内容，不要有任何解释性文字。"""


async def edit_document_tool(params: dict, chat_id: str = "") -> dict:
    doc_id = params.get("document_id") or params.get("documentId")
    action = params.get("action", "append")
    instruction = params.get("instruction", "")
    section = params.get("section", "")
    content = params.get("content", "")

    if not doc_id:
        return {"error": "Missing document_id", "message": "未指定要编辑的文档"}

    db = await get_db()
    cursor = await db.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        return {"error": "Document not found", "message": "文档不存在"}

    doc = dict(row)
    original_content = doc.get("content", "")
    await db.close()

    new_content = await _apply_edit(original_content, action, instruction, section, content)

    db = await get_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await db.execute(
        "UPDATE documents SET content = %s, updated_at = %s WHERE id = %s",
        (new_content, now, doc_id)
    )
    await db.commit()
    await db.close()

    await manager.broadcast({
        "type": "document_updated",
        "data": {"id": doc_id, "title": doc["title"], "content": new_content, "updated_at": now}
    })

    return {
        "document_id": doc_id,
        "title": doc["title"],
        "message": f"文档「{doc['title']}」已更新",
        "artifact": {
            "type": "document",
            "id": doc_id,
            "title": doc["title"],
        }
    }


async def _apply_edit(original: str, action: str, instruction: str, section: str, content: str) -> str:
    if action == "append" and content:
        return original + "\n\n" + content

    if not ARK_API_KEY:
        if action == "append":
            return original + f"\n\n## {section or '新增内容'}\n\n{content or instruction}"
        elif action == "replace" and section:
            return original + f"\n\n[已修改章节: {section}]"
        return original + f"\n\n{instruction or content}"

    try:
        client = AsyncOpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
        prompt = f"""请根据以下指令修改文档：

操作类型：{action}
修改指令：{instruction}
目标章节：{section}
新内容（如有）：{content}

原文档内容：
{original[:4000]}"""

        response = await client.chat.completions.create(
            model=ARK_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": EDIT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        if content:
            return original + f"\n\n{content}"
        return original
