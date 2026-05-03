import uuid
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from database import get_db
from models import AgentRequest
from ws_manager import manager
from agent.orchestrator import AgentOrchestrator

router = APIRouter(tags=["Agent"])
orchestrator = AgentOrchestrator()


@router.post("/agent/chat")
async def agent_chat(req: AgentRequest, background_tasks: BackgroundTasks):
    """Submit a message to the Agent. Triggers intent parsing and task execution."""
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()

    db = await get_db()
    await db.execute("""
        INSERT INTO tasks (id, chat_id, user_id, status, created_at, updated_at)
        VALUES (?, ?, ?, 'processing', ?, ?)
    """, (task_id, req.chat_id, req.user_id, now, now))
    await db.commit()
    await db.close()

    background_tasks.add_task(
        orchestrator.process_message,
        task_id=task_id,
        message=req.message,
        chat_id=req.chat_id,
        user_id=req.user_id,
    )

    return {"task_id": task_id, "status": "processing"}


@router.get("/agent/tasks/{task_id}")
async def get_task(task_id: str):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    task = dict(row)
    if task.get("plan"):
        try:
            task["plan"] = json.loads(task["plan"])
        except (json.JSONDecodeError, TypeError):
            pass
    if task.get("result"):
        try:
            task["result"] = json.loads(task["result"])
        except (json.JSONDecodeError, TypeError):
            pass
    return task


@router.post("/agent/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    db = await get_db()
    await db.execute(
        "UPDATE tasks SET status = 'cancelled', updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), task_id)
    )
    await db.commit()
    await db.close()
    return {"status": "cancelled"}
