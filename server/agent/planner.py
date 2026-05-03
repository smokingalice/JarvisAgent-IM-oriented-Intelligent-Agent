import json
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """你是 Agent-Pilot 的任务规划器。

你的职责：根据用户在 IM 中的消息，理解意图并生成执行计划。

可用工具：
- create_document: 创建新文档（需要标题和大纲）
- edit_document: 编辑已有文档
- create_slides: 创建演示稿/PPT（可基于文档或直接创建）
- edit_slides: 编辑演示稿
- summarize_chat: 总结聊天内容
- general_reply: 普通对话回复（不需要创建任何产出物时使用）

规则：
1. 如果用户只是闲聊或问问题，使用 general_reply
2. 如果信息不足以开始任务，在 clarifications_needed 中提出问题
3. 任务之间有依赖关系时，用 depends_on 标注
4. 每个任务都要有清晰的 name 和合理的 params

输出 JSON 格式（严格遵守）：
{
  "intent": "用一句话描述用户意图",
  "clarifications_needed": [],
  "tasks": [
    {
      "id": "step_1",
      "name": "任务名称",
      "tool": "工具名",
      "params": {},
      "depends_on": []
    }
  ]
}

只输出 JSON，不要有任何其他文字。"""


class Planner:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

    async def create_plan(self, message: str, chat_id: str, user_id: str) -> dict:
        if not self.client:
            return self._fallback_plan(message)

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception as e:
            return self._fallback_plan(message)

    def _fallback_plan(self, message: str) -> dict:
        """Fallback when no API key or API call fails — use keyword matching."""
        msg_lower = message.lower()

        if any(kw in msg_lower for kw in ["写", "生成", "创建", "写一份", "帮我写"]):
            has_doc = any(kw in msg_lower for kw in ["文档", "方案", "报告", "文章"])
            has_ppt = any(kw in msg_lower for kw in ["ppt", "演示", "幻灯片", "slides"])

            tasks = []
            if has_doc or (not has_ppt):
                title = self._extract_title(message)
                tasks.append({
                    "id": "step_1",
                    "name": f"生成文档：{title}",
                    "tool": "create_document",
                    "params": {
                        "title": title,
                        "outline": ["概述", "核心内容", "详细说明", "总结"],
                        "tone": "formal",
                        "source_message": message,
                    },
                    "depends_on": [],
                })
            if has_ppt:
                tasks.append({
                    "id": f"step_{len(tasks) + 1}",
                    "name": "生成演示稿",
                    "tool": "create_slides",
                    "params": {
                        "title": self._extract_title(message),
                        "num_slides": 8,
                        "source_doc": tasks[0]["id"] if tasks else None,
                    },
                    "depends_on": [tasks[0]["id"]] if tasks else [],
                })

            if not tasks:
                tasks.append({
                    "id": "step_1",
                    "name": f"生成文档",
                    "tool": "create_document",
                    "params": {
                        "title": self._extract_title(message),
                        "outline": ["概述", "核心内容", "详细说明", "总结"],
                        "tone": "formal",
                        "source_message": message,
                    },
                    "depends_on": [],
                })

            intent = "创建" + ("文档" if has_doc else "") + ("和" if has_doc and has_ppt else "") + ("演示稿" if has_ppt else "文档")
            return {
                "intent": intent,
                "clarifications_needed": [],
                "tasks": tasks,
            }

        if any(kw in msg_lower for kw in ["总结", "整理", "归纳"]):
            return {
                "intent": "总结对话内容",
                "clarifications_needed": [],
                "tasks": [{
                    "id": "step_1",
                    "name": "总结聊天记录",
                    "tool": "summarize_chat",
                    "params": {"source_message": message},
                    "depends_on": [],
                }],
            }

        return {
            "intent": "回复用户消息",
            "clarifications_needed": [],
            "tasks": [{
                "id": "step_1",
                "name": "回复用户",
                "tool": "general_reply",
                "params": {"message": message},
                "depends_on": [],
            }],
        }

    def _extract_title(self, message: str) -> str:
        for prefix in ["帮我写一份", "帮我写", "帮我生成", "帮我创建", "写一份", "写一个", "生成", "创建"]:
            if prefix in message:
                rest = message.split(prefix, 1)[1]
                title = rest.split("，")[0].split(",")[0].split("。")[0].split("\n")[0].strip()
                if len(title) > 30:
                    title = title[:30]
                return title if title else "未命名文档"
        words = message.replace("帮我", "").replace("请", "").strip()
        return words[:20] if words else "未命名文档"
