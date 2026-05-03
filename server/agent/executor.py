import asyncio
from typing import Callable
from agent.tools.create_document import create_document_tool
from agent.tools.create_slides import create_slides_tool
from agent.tools.summarize_chat import summarize_chat_tool
from agent.tools.general_reply import general_reply_tool


TOOL_REGISTRY = {
    "create_document": create_document_tool,
    "create_slides": create_slides_tool,
    "summarize_chat": summarize_chat_tool,
    "general_reply": general_reply_tool,
}


class Executor:
    """Executes a plan by calling tools in dependency order."""

    async def execute_plan(
        self,
        task_id: str,
        plan: dict,
        chat_id: str,
        progress_callback: Callable = None,
    ) -> dict:
        tasks = plan.get("tasks", [])
        total_steps = len(tasks)
        results = {}
        artifacts = []

        for i, step in enumerate(tasks):
            step_id = step.get("id", f"step_{i}")
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            step_name = step.get("name", tool_name)

            progress = 30 + int((i / max(total_steps, 1)) * 60)
            if progress_callback:
                await progress_callback(step_name, progress, f"正在执行：{step_name}...")

            deps = step.get("depends_on", [])
            for dep_id in deps:
                if dep_id in results:
                    params["_dep_result"] = results[dep_id]

            tool_fn = TOOL_REGISTRY.get(tool_name)
            if not tool_fn:
                results[step_id] = {"error": f"Unknown tool: {tool_name}"}
                continue

            try:
                result = await tool_fn(params, chat_id=chat_id)
                results[step_id] = result
                if result.get("artifact"):
                    artifacts.append(result["artifact"])
            except Exception as e:
                results[step_id] = {"error": str(e)}

        if progress_callback:
            await progress_callback("完成", 95, "任务执行完毕，正在整理结果...")

        return {
            "task_id": task_id,
            "artifacts": artifacts,
            "steps": results,
            "message": f"成功完成 {total_steps} 个步骤",
        }
