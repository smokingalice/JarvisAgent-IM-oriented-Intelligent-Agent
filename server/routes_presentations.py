import json
from fastapi import APIRouter, HTTPException
from database import get_db
from ws_manager import manager

router = APIRouter(tags=["Presentations"])


@router.get("/presentations")
async def list_presentations():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM presentations ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    presentations = []
    for row in rows:
        pres = dict(row)
        if pres.get("slides"):
            try:
                pres["slides"] = json.loads(pres["slides"])
            except (json.JSONDecodeError, TypeError):
                pass
        presentations.append(pres)
    return presentations


@router.get("/presentations/{pres_id}")
async def get_presentation(pres_id: str):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM presentations WHERE id = ?", (pres_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Presentation not found")
    pres = dict(row)
    if pres.get("slides"):
        try:
            pres["slides"] = json.loads(pres["slides"])
        except (json.JSONDecodeError, TypeError):
            pass
    return pres


@router.patch("/presentations/{pres_id}")
async def update_presentation(pres_id: str, updates: dict):
    db = await get_db()
    allowed = ["title", "slides", "template"]
    set_clauses = []
    values = []
    for key in allowed:
        if key in updates:
            set_clauses.append(f"{key} = ?")
            val = updates[key]
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            values.append(val)
    if not set_clauses:
        await db.close()
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_clauses.append("updated_at = datetime('now')")
    values.append(pres_id)
    await db.execute(
        f"UPDATE presentations SET {', '.join(set_clauses)} WHERE id = ?", values
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM presentations WHERE id = ?", (pres_id,))
    row = await cursor.fetchone()
    await db.close()
    pres = dict(row)

    await manager.broadcast({
        "type": "presentation_updated",
        "data": pres,
    })
    return pres
