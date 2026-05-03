from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY


async def general_reply_tool(params: dict, chat_id: str = "") -> dict:
    message = params.get("message", "")

    if not ANTHROPIC_API_KEY:
        return {"message": f"收到你的消息。我是 Agent-Pilot，可以帮你生成文档、制作PPT、总结聊天内容等。试试对我说「帮我写一份产品方案」？"}

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="""你是 Agent-Pilot，一个 AI 协同办公助手。你可以帮用户：
1. 生成文档（方案、报告、文章等）
2. 制作演示稿/PPT
3. 总结聊天讨论

保持回复简洁友好，如果用户的意图不明确，主动引导他们使用你的能力。""",
            messages=[{"role": "user", "content": message}],
        )
        return {"message": response.content[0].text}
    except Exception:
        return {"message": "我是 Agent-Pilot，你的 AI 协同助手。有什么我可以帮你的吗？比如生成文档、制作PPT或者总结讨论内容。"}
