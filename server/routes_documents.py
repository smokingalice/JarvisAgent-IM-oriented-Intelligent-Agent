import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
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
    cursor = await db.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
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
            set_clauses.append(f"{key} = %s")
            val = updates[key]
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            values.append(val)
    if not set_clauses:
        await db.close()
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_clauses.append("updated_at = NOW()")
    values.append(doc_id)
    await db.execute(
        f"UPDATE documents SET {', '.join(set_clauses)} WHERE id = %s", values
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    row = await cursor.fetchone()
    await db.close()
    doc = dict(row)

    await manager.broadcast({
        "type": "document_updated",
        "data": doc,
    })
    return doc


@router.get("/documents/{doc_id}/export")
async def export_document(doc_id: str, format: str = "md"):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = dict(row)
    title = doc.get("title", "untitled")
    content = doc.get("content", "")

    if format == "md":
        md_content = f"# {title}\n\n{content}"
        return PlainTextResponse(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{title}.md"'},
        )
    elif format == "html":
        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui;max-width:800px;margin:40px auto;padding:0 20px;line-height:1.6}}</style>
</head><body><h1>{title}</h1><div>{_md_to_html(content)}</div></body></html>"""
        return HTMLResponse(
            content=html_content,
            headers={"Content-Disposition": f'attachment; filename="{title}.html"'},
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'md' or 'html'.")


def _md_to_html(md: str) -> str:
    lines = md.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{line}</p>")
    return "\n".join(html_lines)
