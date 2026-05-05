import uuid
import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_DEFAULT_SONNET_MODEL
from database import get_db
from agent.llm_debug import extract_response_text, log_llm_error


async def summarize_chat_tool(params: dict, chat_id: str = "") -> dict:
    db = await get_db()
    cursor = await db.execute("""
        SELECT m.content, m.sender_id, u.name as sender_name, m.created_at
        FROM messages m
        LEFT JOIN users u ON m.sender_id = u.id
        WHERE m.chat_id = ? AND m.recalled_at IS NULL AND m.sender_id != 'agent'
        ORDER BY m.created_at DESC LIMIT 30
    """, (chat_id,))
    rows = await cursor.fetchall()
    await db.close()

    messages = [dict(row) for row in rows]
    messages.reverse()

    if not messages:
        return {"message": "当前聊天没有找到可总结的消息。"}

    chat_text = "\n".join(
        f"{msg.get('sender_name', msg['sender_id'])}: {msg['content']}"
        for msg in messages
    )

    summary, generation_mode = await _generate_summary(chat_text, params.get("source_message", ""))

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    db = await get_db()
    await db.execute("""
        INSERT INTO documents (id, title, content, status, created_by, created_at, updated_at)
        VALUES (?, ?, ?, 'finalized', 'agent', ?, ?)
    """, (doc_id, "聊天总结", summary, now, now))
    await db.commit()
    await db.close()

    return {
        "document_id": doc_id,
        "summary": summary,
        "message_count": len(messages),
        "generation_mode": generation_mode,
        "model": ANTHROPIC_DEFAULT_SONNET_MODEL if generation_mode == "llm" else None,
        "artifact": {
            "type": "document",
            "id": doc_id,
            "title": "聊天总结",
        }
    }


async def _generate_summary(chat_text: str, user_request: str) -> tuple[str, str]:
    if not ANTHROPIC_API_KEY:
        return f"# 聊天总结\n\n共 {chat_text.count(chr(10)) + 1} 条消息的讨论总结。\n\n## 主要讨论内容\n\n{chat_text[:500]}", "fallback"

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)
        response = await client.messages.create(
            model=ANTHROPIC_DEFAULT_SONNET_MODEL,
            max_tokens=2048,
            system="你是一个专业的会议/对话总结助手。请将聊天内容总结为结构化的文档，包含：讨论要点、决策事项、待办事项。输出 Markdown 格式。",
            messages=[{"role": "user", "content": f"用户要求：{user_request}\n\n聊天记录：\n{chat_text}"}],
        )
        return extract_response_text(response), "llm"
    except Exception as e:
        log_llm_error("summarize_chat_tool", e)
        return f"# 聊天总结\n\n共 {chat_text.count(chr(10)) + 1} 条消息。\n\n## 讨论内容概要\n\n{chat_text[:500]}", "fallback"
