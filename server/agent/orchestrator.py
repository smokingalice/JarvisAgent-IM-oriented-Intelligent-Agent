import json
import uuid
import asyncio
from datetime import datetime
from database import get_db
from ws_manager import manager
from agent.planner import Planner
from agent.executor import Executor


class AgentOrchestrator:
    """Main Agent orchestration engine.

    Flow: message -> context analysis -> intent classification -> planning -> execution -> delivery
    Proactive abilities: clarification, discussion summary, context-based recommendations.
    """

    def __init__(self):
        self.planner = Planner()
        self.executor = Executor()

    async def process_message(self, task_id: str, message: str, chat_id: str, user_id: str):
        try:
            await self._send_agent_message(
                chat_id, "收到！正在分析你的需求...", msg_type="text"
            )
            await self._update_task(task_id, status="planning", progress=10)

            context = await self._gather_chat_context(chat_id)

            proactive_action = self._check_proactive_triggers(message, context)
            if proactive_action:
                await self._handle_proactive_action(proactive_action, task_id, chat_id, context)
                return

            plan = await self.planner.create_plan(message, chat_id, user_id, context=context)

            await self._update_task(
                task_id, status="planned", progress=20,
                intent=plan.get("intent", ""),
                plan=plan.get("tasks", []),
            )

            if plan.get("clarifications_needed"):
                clarification_msg = self._format_clarification(plan["clarifications_needed"], message)
                await self._send_agent_message(chat_id, clarification_msg, msg_type="agent_card", card_data={
                    "type": "clarification",
                    "title": "需要确认几个细节",
                    "questions": plan["clarifications_needed"],
                    "task_id": task_id,
                })
                return

            plan_summary = self._format_plan_summary(plan)
            await self._send_agent_message(chat_id, plan_summary, msg_type="agent_card", card_data={
                "type": "plan",
                "task_id": task_id,
                "tasks": plan.get("tasks", []),
            })

            await self._update_task(task_id, status="executing", progress=30)

            results = await self.executor.execute_plan(
                task_id=task_id,
                plan=plan,
                chat_id=chat_id,
                progress_callback=self._make_progress_callback(task_id, chat_id),
            )

            await self._update_task(task_id, status="completed", progress=100, result=results)

            delivery_msg = self._format_delivery(results)
            await self._send_agent_message(chat_id, delivery_msg, msg_type="agent_card", card_data={
                "type": "delivery",
                "task_id": task_id,
                "results": results,
            })

        except Exception as e:
            await self._update_task(task_id, status="failed", result={"error": str(e)})
            await self._send_agent_message(
                chat_id, f"抱歉，任务执行遇到问题：{str(e)}\n\n请重试或换一种方式描述你的需求。"
            )

    async def _gather_chat_context(self, chat_id: str) -> dict:
        """Gather recent chat history for context-aware planning."""
        db = await get_db()
        cursor = await db.execute("""
            SELECT content, sender_id, msg_type, created_at
            FROM messages
            WHERE chat_id = ? AND recalled_at IS NULL
            ORDER BY created_at DESC LIMIT 20
        """, (chat_id,))
        rows = await cursor.fetchall()

        cursor2 = await db.execute("""
            SELECT id, title, type FROM (
                SELECT id, title, 'document' as type, updated_at FROM documents
                UNION ALL
                SELECT id, title, 'presentation' as type, updated_at FROM presentations
            ) ORDER BY updated_at DESC LIMIT 5
        """)
        recent_artifacts = [dict(r) for r in await cursor2.fetchall()]
        await db.close()

        messages = [dict(row) for row in rows]
        messages.reverse()
        return {
            "recent_messages": messages,
            "message_count": len(messages),
            "recent_artifacts": recent_artifacts,
            "has_long_discussion": len(messages) >= 15,
        }

    def _check_proactive_triggers(self, message: str, context: dict) -> dict | None:
        """Check if the Agent should proactively intervene."""
        msg_lower = message.lower()

        if context.get("has_long_discussion") and any(
            kw in msg_lower for kw in ["总结一下", "说了什么", "梳理", "回顾"]
        ):
            return {"action": "summarize_discussion", "reason": "user_requested"}

        if context.get("has_long_discussion") and context["message_count"] >= 18:
            non_agent = [m for m in context["recent_messages"] if m["sender_id"] != "agent"]
            if len(non_agent) >= 15:
                return {"action": "suggest_summary", "reason": "long_discussion"}

        if any(kw in msg_lower for kw in ["接下来", "还能做什么", "下一步", "然后呢"]):
            return {"action": "recommend_next", "reason": "user_asked"}

        return None

    async def _handle_proactive_action(self, action: dict, task_id: str, chat_id: str, context: dict):
        """Handle proactive Agent actions."""
        action_type = action["action"]

        if action_type == "suggest_summary":
            await self._update_task(task_id, status="completed", progress=100)
            msg = (
                "💡 我注意到大家已经讨论了很多内容，要不要我帮你：\n\n"
                "1. **总结本次讨论** — 提炼要点、决策和待办\n"
                "2. **基于讨论生成文档** — 把讨论结果整理成正式文档\n"
                "3. **继续当前话题** — 我可以参与讨论\n\n"
                "回复数字或直接告诉我你的需求。"
            )
            await self._send_agent_message(chat_id, msg, msg_type="agent_card", card_data={
                "type": "recommendation",
                "title": "Agent 建议",
                "options": ["总结讨论", "生成文档", "继续讨论"],
                "task_id": task_id,
            })

        elif action_type == "recommend_next":
            await self._update_task(task_id, status="completed", progress=100)
            suggestions = self._context_recommendations(context)
            lines = ["🧭 **根据当前上下文，我建议：**\n"]
            for i, s in enumerate(suggestions, 1):
                lines.append(f"  {i}. {s}")
            lines.append("\n直接告诉我你想做什么，或者回复编号。")
            await self._send_agent_message(chat_id, "\n".join(lines), msg_type="agent_card", card_data={
                "type": "recommendation",
                "title": "下一步建议",
                "options": suggestions,
                "task_id": task_id,
            })

    def _context_recommendations(self, context: dict) -> list:
        """Generate context-aware recommendations."""
        suggestions = []
        artifacts = context.get("recent_artifacts", [])
        has_doc = any(a["type"] == "document" for a in artifacts)
        has_pres = any(a["type"] == "presentation" for a in artifacts)

        if has_doc and not has_pres:
            suggestions.append("把最近的文档转成演示稿")
        if has_pres and not has_doc:
            suggestions.append("为演示稿生成配套文档/讲稿")
        if context.get("has_long_discussion"):
            suggestions.append("总结本次讨论要点")
        if artifacts:
            suggestions.append("导出已有成果")
            suggestions.append("对现有内容进行修改优化")
        if not artifacts:
            suggestions.append("生成一份文档（方案/报告/总结）")
            suggestions.append("创建一份演示稿")
        suggestions.append("把成果分享给同事")
        return suggestions[:5]

    def _format_clarification(self, questions: list, original_message: str) -> str:
        """Format clarification questions into a structured card message."""
        lines = [f"为了更好地完成你的需求，我需要确认几个细节：\n"]
        for i, q in enumerate(questions, 1):
            lines.append(f"  **{i}.** {q}")
        lines.append("\n请回复相关信息，我会立即开始执行。")
        return "\n".join(lines)

    def _make_progress_callback(self, task_id: str, chat_id: str):
        async def callback(step_name: str, progress: int, message: str):
            await self._update_task(task_id, progress=progress)
            await manager.broadcast({
                "type": "task_progress",
                "data": {
                    "task_id": task_id,
                    "step": step_name,
                    "progress": progress,
                    "message": message,
                }
            })
        return callback

    def _format_plan_summary(self, plan: dict) -> str:
        lines = [f"好的，我来帮你完成这个任务。\n"]
        lines.append(f"**目标**：{plan.get('intent', '执行任务')}\n")
        lines.append("**执行计划**：")
        for i, task in enumerate(plan.get("tasks", []), 1):
            icon = "📄" if "doc" in task.get("tool", "") else "📊" if "slide" in task.get("tool", "") else "🔧"
            lines.append(f"  {i}. {icon} {task.get('name', task.get('tool', ''))}")
        lines.append("\n正在执行中...")
        return "\n".join(lines)

    def _format_delivery(self, results: dict) -> str:
        lines = ["✅ **任务完成！**\n\n以下是本次工作成果：\n"]
        artifacts = results.get("artifacts", [])
        for art in artifacts:
            if art["type"] == "document":
                lines.append(f"📄 **{art['title']}**")
                lines.append(f"   文档ID: {art['id']}")
            elif art["type"] == "presentation":
                lines.append(f"📊 **{art['title']}** ({art.get('slide_count', '?')}页)")
                lines.append(f"   演示稿ID: {art['id']}")
        if not artifacts:
            lines.append(results.get("message", "任务已完成。"))

        suggestions = self._generate_proactive_suggestions(artifacts)
        if suggestions:
            lines.append("\n💡 **接下来你可能需要：**")
            for s in suggestions:
                lines.append(f"  • {s}")

        lines.append("\n需要修改或有其他需求吗？")
        return "\n".join(lines)

    def _generate_proactive_suggestions(self, artifacts: list) -> list:
        suggestions = []
        has_doc = any(a["type"] == "document" for a in artifacts)
        has_pres = any(a["type"] == "presentation" for a in artifacts)

        if has_doc and not has_pres:
            suggestions.append('基于这份文档生成演示稿（说「帮我做成PPT」）')
            suggestions.append('导出为 Markdown 或 HTML（说「导出文档」）')
        elif has_pres and not has_doc:
            suggestions.append('生成配套的文字稿/讲稿（说「帮我写讲稿」）')
            suggestions.append('导出演示稿（说「导出PPT」）')
        elif has_doc and has_pres:
            suggestions.append('导出所有成果（说「导出全部」）')
            suggestions.append('对内容进行修改（说「修改一下XXX部分」）')

        if artifacts:
            suggestions.append('分享给同事（说「分享给XXX」）')

        return suggestions

    async def _send_agent_message(self, chat_id: str, content: str, msg_type: str = "text", card_data: dict = None):
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        db = await get_db()
        card_json = json.dumps(card_data, ensure_ascii=False) if card_data else None
        await db.execute("""
            INSERT INTO messages (id, chat_id, sender_id, content, msg_type, card_data, created_at)
            VALUES (?, ?, 'agent', ?, ?, ?, ?)
        """, (msg_id, chat_id, content, msg_type, card_json, now))
        await db.commit()
        await db.close()

        message = {
            "id": msg_id,
            "chat_id": chat_id,
            "sender_id": "agent",
            "content": content,
            "msg_type": msg_type,
            "card_data": card_data,
            "created_at": now,
            "recalled_at": None,
        }
        await manager.broadcast({"type": "new_message", "data": message})

    async def _update_task(self, task_id: str, **kwargs):
        db = await get_db()
        set_clauses = ["updated_at = ?"]
        values = [datetime.utcnow().isoformat()]
        for key, val in kwargs.items():
            if key in ("status", "progress", "intent"):
                set_clauses.append(f"{key} = ?")
                values.append(val)
            elif key == "plan":
                set_clauses.append("plan = ?")
                values.append(json.dumps(val, ensure_ascii=False))
            elif key == "result":
                set_clauses.append("result = ?")
                values.append(json.dumps(val, ensure_ascii=False))
        values.append(task_id)
        await db.execute(
            f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?", values
        )
        await db.commit()
        await db.close()

        await manager.broadcast({
            "type": "task_update",
            "data": {"task_id": task_id, **kwargs}
        })
