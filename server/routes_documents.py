import json
from fastapi import APIRouter, HTTPException
from database import get_db
from ws_manager import manager

router = APIRouter(tags=["Documents"])


@router.get("/documents")
async def list_documents():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM documents ORDER BY updated_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    docs = []
    for row in rows:
        doc = dict(row)
        if doc.get("outline"):
            try:
                doc["outline"] = json.loads(doc["outline"])
            except (json.JSONDecodeError, TypeError):
                pass
        docs.append(doc)
    return docs


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = dict(row)
    if doc.get("outline"):
        try:
            doc["outline"] = json.loads(doc["outline"])
        except (json.JSONDecodeError, TypeError):
            pass
    return doc


@router.patch("/documents/{doc_id}")
async def update_document(doc_id: str, updates: dict):
    db = await get_db()
    allowed = ["title", "content", "outline", "status"]
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
    values.append(doc_id)
    await db.execute(
        f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = ?", values
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = await cursor.fetchone()
    await db.close()
    doc = dict(row)

    await manager.broadcast({
        "type": "document_updated",
        "data": doc,
    })
    return doc
