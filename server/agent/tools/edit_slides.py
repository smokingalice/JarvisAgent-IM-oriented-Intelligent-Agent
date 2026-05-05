import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from database import get_db
from ws_manager import manager

EDIT_SLIDES_PROMPT = """你是一个演示稿编辑助手。根据用户指令修改演示稿的 JSON 数据。

可用的布局类型：
- title: 标题页（title, subtitle）
- content: 内容页（title, points[]）
- two_column: 双栏对比（title, left_title, left_points[], right_title, right_points[]）
- image_text: 图文页（title, text）
- summary: 总结页（title, points[]）

输出修改后的完整 slides JSON 数组。只输出 JSON，不要有任何其他文字。"""


async def edit_slides_tool(params: dict, chat_id: str = "") -> dict:
    pres_id = params.get("presentation_id") or params.get("presentationId")
    instruction = params.get("instruction", "")
    action = params.get("action", "update_text")
    slide_id = params.get("slide_id") or params.get("slideId")

    if not pres_id:
        return {"error": "Missing presentation_id", "message": "未指定要编辑的演示稿"}

    db = await get_db()
    cursor = await db.execute("SELECT * FROM presentations WHERE id = ?", (pres_id,))
    row = await cursor.fetchone()
    if not row:
        await db.close()
        return {"error": "Presentation not found", "message": "演示稿不存在"}

    pres = dict(row)
    slides_raw = pres.get("slides", "[]")
    try:
        slides = json.loads(slides_raw) if isinstance(slides_raw, str) else slides_raw
    except (json.JSONDecodeError, TypeError):
        slides = []
    await db.close()

    new_slides = await _apply_slides_edit(slides, instruction, action, slide_id)

    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.execute(
        "UPDATE presentations SET slides = ?, updated_at = ? WHERE id = ?",
        (json.dumps(new_slides, ensure_ascii=False), now, pres_id)
    )
    await db.commit()
    await db.close()

    await manager.broadcast({
        "type": "presentation_updated",
        "data": {"id": pres_id, "title": pres["title"], "slides": new_slides, "updated_at": now}
    })

    return {
        "presentation_id": pres_id,
        "title": pres["title"],
        "slide_count": len(new_slides),
        "message": f"演示稿「{pres['title']}」已更新",
        "artifact": {
            "type": "presentation",
            "id": pres_id,
            "title": pres["title"],
            "slide_count": len(new_slides),
        }
    }


async def _apply_slides_edit(slides: list, instruction: str, action: str, slide_id: str = None) -> list:
    if not ANTHROPIC_API_KEY:
        return slides

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)
        prompt = f"""请根据以下指令修改演示稿：

修改指令：{instruction}
操作类型：{action}
目标幻灯片编号：{slide_id or "不指定"}

当前演示稿内容：
{json.dumps(slides, ensure_ascii=False, indent=2)[:3000]}"""

        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=EDIT_SLIDES_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return slides
