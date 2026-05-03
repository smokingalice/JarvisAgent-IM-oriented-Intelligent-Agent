import uuid
import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY
from database import get_db

SLIDES_SYSTEM_PROMPT = """你是一个专业的演示稿设计师。根据文档内容或用户需求，生成结构化的演示稿数据。

可用的布局类型：
- title: 标题页（有 title 和 subtitle）
- content: 内容页（有 title 和 points 列表）
- two_column: 双栏对比（有 title, left_title, left_points, right_title, right_points）
- image_text: 图文页（有 title, text, image_description）
- summary: 总结页（有 title 和 points）

输出 JSON 数组格式，每个元素是一页幻灯片：
[
  {"layout": "title", "data": {"title": "...", "subtitle": "..."}},
  {"layout": "content", "data": {"title": "...", "points": ["...", "..."]}},
  ...
]

要求：
1. 第一页必须是 title 布局
2. 最后一页必须是 summary 布局
3. 中间页面交替使用不同布局，让演示更丰富
4. 每页的 points 不超过 5 个要点
5. 总页数按用户要求，默认 8 页

只输出 JSON 数组，不要有任何其他文字。"""


async def create_slides_tool(params: dict, chat_id: str = "") -> dict:
    title = params.get("title", "未命名演示稿")
    num_slides = params.get("num_slides", 8)
    source_doc = params.get("source_doc")
    dep_result = params.get("_dep_result", {})

    source_content = ""
    source_doc_id = dep_result.get("document_id") or source_doc
    if source_doc_id:
        db = await get_db()
        cursor = await db.execute("SELECT content, title FROM documents WHERE id = ?", (source_doc_id,))
        row = await cursor.fetchone()
        await db.close()
        if row:
            source_content = dict(row).get("content", "")
            if not title or title == "未命名演示稿":
                title = dict(row).get("title", title)

    slides = await _generate_slides(title, num_slides, source_content, params.get("source_message", ""))

    pres_id = f"ppt_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    db = await get_db()
    await db.execute("""
        INSERT INTO presentations (id, title, slides, source_doc_id, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'agent', ?, ?)
    """, (pres_id, title, json.dumps(slides, ensure_ascii=False), source_doc_id, now, now))
    await db.commit()
    await db.close()

    return {
        "presentation_id": pres_id,
        "title": title,
        "slide_count": len(slides),
        "artifact": {
            "type": "presentation",
            "id": pres_id,
            "title": title,
            "slide_count": len(slides),
        }
    }


async def _generate_slides(title: str, num_slides: int, source_content: str, source_message: str) -> list:
    if not ANTHROPIC_API_KEY:
        return _fallback_slides(title, num_slides)

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        prompt = f"""请为以下演示稿生成 {num_slides} 页幻灯片内容：

标题：{title}
页数：{num_slides}
"""
        if source_content:
            prompt += f"\n基于以下文档内容提炼要点：\n{source_content[:3000]}"
        if source_message:
            prompt += f"\n用户原始需求：{source_message}"

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SLIDES_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return _fallback_slides(title, num_slides)


def _fallback_slides(title: str, num_slides: int) -> list:
    slides = [
        {"layout": "title", "data": {"title": title, "subtitle": "AI 驱动的智能协同办公"}},
        {"layout": "content", "data": {"title": "项目概述", "points": ["项目背景与目标", "核心问题与挑战", "解决方案概览"]}},
        {"layout": "two_column", "data": {
            "title": "优势对比",
            "left_title": "传统方式", "left_points": ["手动操作", "耗时长", "易出错"],
            "right_title": "智能方案", "right_points": ["自动化", "分钟级完成", "高质量输出"],
        }},
        {"layout": "content", "data": {"title": "核心功能", "points": ["自然语言指令驱动", "智能文档生成", "一键演示稿制作", "多端实时同步"]}},
        {"layout": "content", "data": {"title": "技术架构", "points": ["大语言模型驱动", "Agent 任务编排", "实时通信框架", "跨端统一体验"]}},
        {"layout": "image_text", "data": {"title": "用户体验", "text": "通过自然语言交互，用户只需表达需求，系统自动完成从文档到演示稿的全流程。", "image_description": "用户与AI对话的界面截图"}},
        {"layout": "content", "data": {"title": "实施路线", "points": ["第一阶段：核心引擎搭建", "第二阶段：文档模块上线", "第三阶段：演示稿模块", "第四阶段：多端同步与打磨"]}},
        {"layout": "summary", "data": {"title": "总结与展望", "points": ["AI 重新定义办公协同", "从对话到交付的完整闭环", "持续迭代优化体验"]}},
    ]
    return slides[:num_slides]
