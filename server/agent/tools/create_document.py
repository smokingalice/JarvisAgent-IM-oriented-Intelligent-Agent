import uuid
import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY
from database import get_db

DOC_SYSTEM_PROMPT = """你是一个专业的文档撰写者。根据用户的需求生成结构化的文档内容。

要求：
1. 输出纯 Markdown 格式
2. 使用恰当的标题层级（# ## ###）
3. 内容专业、有条理
4. 每个章节 200-400 字
5. 包含适当的列表、表格等元素增强可读性

只输出文档内容，不要有任何解释性文字。"""


async def create_document_tool(params: dict, chat_id: str = "") -> dict:
    title = params.get("title", "未命名文档")
    outline = params.get("outline", ["概述", "核心内容", "详细说明", "总结"])
    tone = params.get("tone", "formal")
    source_message = params.get("source_message", "")

    content = await _generate_document_content(title, outline, tone, source_message)

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    db = await get_db()
    await db.execute("""
        INSERT INTO documents (id, title, content, outline, status, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'draft', 'agent', ?, ?)
    """, (doc_id, title, content, json.dumps(outline, ensure_ascii=False), now, now))
    await db.commit()
    await db.close()

    return {
        "document_id": doc_id,
        "title": title,
        "artifact": {
            "type": "document",
            "id": doc_id,
            "title": title,
        }
    }


async def _generate_document_content(title: str, outline: list, tone: str, source_message: str) -> str:
    if not ANTHROPIC_API_KEY:
        return _fallback_content(title, outline)

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        tone_desc = {"formal": "正式专业", "casual": "轻松口语化", "technical": "技术文档风格"}.get(tone, "正式专业")

        prompt = f"""请为以下文档生成完整内容：

标题：{title}
大纲章节：{', '.join(outline)}
风格：{tone_desc}
用户原始需求：{source_message}

请按照大纲逐章节撰写完整内容。"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=DOC_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception:
        return _fallback_content(title, outline)


def _fallback_content(title: str, outline: list) -> str:
    lines = [f"# {title}\n"]
    for section in outline:
        lines.append(f"## {section}\n")
        lines.append(f"{section}的详细内容将在此处展开。本章节将围绕{title}的{section}方面进行深入分析和阐述。\n")
        lines.append("- 要点一：核心概念说明")
        lines.append("- 要点二：具体实施方案")
        lines.append("- 要点三：预期效果与评估\n")
    return "\n".join(lines)
