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

    Flow: message -> intent classification -> planning -> execution -> delivery
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

            plan = await self.planner.create_plan(message, chat_id, user_id)

            await self._update_task(
                task_id, status="planned", progress=20,
                intent=plan.get("intent", ""),
                plan=plan.get("tasks", []),
            )

            if plan.get("clarifications_needed"):
                question = plan["clarifications_needed"][0]
                await self._send_agent_message(chat_id, question, msg_type="agent_card", card_data={
                    "type": "clarification",
                    "question": question,
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
        lines.append("\n需要修改或有其他需求吗？")
        return "\n".join(lines)

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
