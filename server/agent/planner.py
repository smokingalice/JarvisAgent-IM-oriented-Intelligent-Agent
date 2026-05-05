import json
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL

SYSTEM_PROMPT = """你是 JarvisAgent 的任务规划器。

你的职责：根据用户在 IM 中的消息，理解意图并生成执行计划。

可用工具：
- create_document: 创建新文档（需要标题和大纲）
- edit_document: 编辑已有文档（需要 document_id、action、instruction）
- create_slides: 创建演示稿/PPT（可基于文档或直接创建）
- edit_slides: 编辑已有演示稿（需要 presentation_id、action、instruction）
- summarize_chat: 总结聊天内容
- share_deliverable: 分享交付物（需要 resource_id、resource_type）
- insert_rich_content: 在文档中插入富媒体（表格、图片占位、布局调整）
- general_reply: 普通对话回复（不需要创建任何产出物时使用）

规则：
1. 如果用户只是闲聊或问问题，使用 general_reply
2. 如果信息不足以开始任务，在 clarifications_needed 中提出问题
3. 任务之间有依赖关系时，用 depends_on 标注
4. 每个任务都要有清晰的 name 和合理的 params
5. 如果用户说"修改"、"改一下"、"加上"等编辑指令，使用 edit_document 或 edit_slides
6. 如果用户说"分享"、"发给"等，使用 share_deliverable

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
        self.client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL) if ANTHROPIC_API_KEY else None

    async def create_plan(self, message: str, chat_id: str, user_id: str, context: dict = None) -> dict:
        if not self.client:
            return self._fallback_plan(message, context)

        try:
            context_str = ""
            if context and context.get("recent_messages"):
                recent = context["recent_messages"][-5:]
                context_str = "\n最近的对话上下文：\n" + "\n".join(
                    f"  {m['sender_id']}: {m['content'][:100]}" for m in recent if m.get("content")
                )
            if context and context.get("recent_artifacts"):
                context_str += "\n已有的产出物：" + ", ".join(
                    f"{a['title']}({a['type']})" for a in context["recent_artifacts"]
                )

            response = await self.client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": message + context_str}],
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(text)
        except Exception:
            return self._fallback_plan(message, context)

    def _fallback_plan(self, message: str, context: dict = None) -> dict:
        """Fallback when no API key or API call fails — use keyword matching."""
        msg_lower = message.lower()

        # Edit commands
        if any(kw in msg_lower for kw in ["修改", "改一下", "加上", "添加", "删除", "替换", "更新"]):
            if any(kw in msg_lower for kw in ["ppt", "演示", "幻灯片", "slides"]):
                return {
                    "intent": "修改演示稿",
                    "clarifications_needed": [],
                    "tasks": [{
                        "id": "step_1",
                        "name": "修改演示稿",
                        "tool": "edit_slides",
                        "params": {"instruction": message, "action": "update_text"},
                        "depends_on": [],
                    }],
                }
            if any(kw in msg_lower for kw in ["文档", "方案", "报告"]):
                return {
                    "intent": "修改文档",
                    "clarifications_needed": [],
                    "tasks": [{
                        "id": "step_1",
                        "name": "修改文档",
                        "tool": "edit_document",
                        "params": {"instruction": message, "action": "replace"},
                        "depends_on": [],
                    }],
                }

        # Share commands
        if any(kw in msg_lower for kw in ["分享", "发给", "共享", "发送"]):
            return {
                "intent": "分享交付物",
                "clarifications_needed": [],
                "tasks": [{
                    "id": "step_1",
                    "name": "分享文件",
                    "tool": "share_deliverable",
                    "params": {"share_to": "current_chat"},
                    "depends_on": [],
                }],
            }

        # Proactive clarification for vague requests
        if any(kw in msg_lower for kw in ["写", "生成", "创建", "帮我写", "做一个"]):
            vague_patterns = ["写点什么", "写个东西", "帮我写", "生成一下", "做一个"]
            is_vague = any(p == msg_lower.strip() for p in vague_patterns) or len(message.strip()) < 6
            if is_vague:
                return {
                    "intent": "需要更多信息",
                    "clarifications_needed": [
                        "你想让我写什么类型的内容？（文档/方案/报告/PPT）",
                        "关于什么主题？",
                        "有没有特定的要求，比如篇幅、风格或受众？",
                    ],
                    "tasks": [],
                }

        # Create commands
        if any(kw in msg_lower for kw in ["写", "生成", "创建", "写一份", "帮我写", "做一个"]):
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
                    "name": "生成文档",
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

        # Rich media / canvas commands
        if any(kw in msg_lower for kw in ["插入表格", "加个表格", "添加表格", "插入图片", "加张图", "布局", "排版"]):
            action = "insert_table" if "表格" in msg_lower else "insert_image" if "图" in msg_lower else "adjust_layout"
            return {
                "intent": "富媒体操作",
                "clarifications_needed": [],
                "tasks": [{
                    "id": "step_1",
                    "name": f"执行富媒体操作: {action}",
                    "tool": "insert_rich_content",
                    "params": {"action": action, "instruction": message},
                    "depends_on": [],
                }],
            }

        # Summarize commands
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

        # Default: general reply
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
        for prefix in ["帮我写一份", "帮我写", "帮我生成", "帮我创建", "写一份", "写一个", "生成", "创建", "做一个", "做一份"]:
            if prefix in message:
                rest = message.split(prefix, 1)[1]
                title = rest.split("，")[0].split(",")[0].split("。")[0].split("\n")[0].strip()
                if len(title) > 30:
                    title = title[:30]
                return title if title else "未命名文档"
        words = message.replace("帮我", "").replace("请", "").strip()
        return words[:20] if words else "未命名文档"
