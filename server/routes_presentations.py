import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
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


@router.get("/presentations/{pres_id}/export")
async def export_presentation(pres_id: str, format: str = "json"):
    db = await get_db()
    cursor = await db.execute("SELECT * FROM presentations WHERE id = ?", (pres_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Presentation not found")
    pres = dict(row)
    title = pres.get("title", "untitled")
    slides_raw = pres.get("slides", "[]")
    if isinstance(slides_raw, str):
        try:
            slides = json.loads(slides_raw)
        except (json.JSONDecodeError, TypeError):
            slides = []
    else:
        slides = slides_raw

    if format == "json":
        export_data = {"title": title, "slides": slides, "template": pres.get("template", "default")}
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": f'attachment; filename="{title}.json"'},
        )
    elif format == "html":
        slides_html = _slides_to_html(title, slides)
        return HTMLResponse(
            content=slides_html,
            headers={"Content-Disposition": f'attachment; filename="{title}.html"'},
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'html'.")


def _slides_to_html(title: str, slides: list) -> str:
    slide_pages = []
    for i, slide in enumerate(slides):
        s_title = slide.get("title", "")
        s_body = slide.get("body", "")
        bullets = slide.get("bullets", [])
        bullets_html = "".join(f"<li>{b}</li>" for b in bullets) if bullets else ""
        slide_pages.append(f"""
<section class="slide">
  <h2>{s_title}</h2>
  {'<p>' + s_body + '</p>' if s_body else ''}
  {'<ul>' + bullets_html + '</ul>' if bullets_html else ''}
  <span class="page">{i+1}/{len(slides)}</span>
</section>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:system-ui;margin:0;background:#1e1e2e}}
.slide{{width:900px;height:500px;margin:40px auto;background:#fff;border-radius:12px;
padding:60px;box-sizing:border-box;position:relative;box-shadow:0 4px 20px rgba(0,0,0,.2)}}
.slide h2{{color:#4F46E5;margin-bottom:20px}}
.slide p{{font-size:18px;line-height:1.6;color:#333}}
.slide ul{{font-size:16px;line-height:1.8;color:#444}}
.page{{position:absolute;bottom:20px;right:30px;color:#999;font-size:13px}}
</style></head><body>{''.join(slide_pages)}</body></html>"""
