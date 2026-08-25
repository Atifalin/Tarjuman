from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from backend.app.database.models import GlossaryItem
from backend.app.terminology.manager import TerminologyManager
from backend.app.database.connection import get_db

router = APIRouter(prefix="/api/glossary", tags=["Glossary & Memory"])

class AddTermRequest(BaseModel):
    project_id: Optional[str] = None
    source_arabic: str
    target_urdu: str
    category: Optional[str] = "General"
    notes: Optional[str] = ""

@router.get("", response_model=List[GlossaryItem])
def get_glossary_terms(project_id: Optional[str] = None):
    return TerminologyManager.get_terms_for_project(project_id)

@router.post("", response_model=GlossaryItem)
def add_glossary_term(req: AddTermRequest):
    item = GlossaryItem(
        project_id=req.project_id,
        source_arabic=req.source_arabic,
        target_urdu=req.target_urdu,
        category=req.category,
        notes=req.notes,
        is_approved=True
    )
    return TerminologyManager.add_term(item)

@router.get("/translation-memory")
def get_translation_memory():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM translation_memory ORDER BY usage_count DESC, updated_at DESC LIMIT 200;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.delete("/translation-memory")
def clear_translation_memory():
    """Wipes all cached Translation Memory entries. Use this if earlier approvals were
    produced by a different/misconfigured model and are now poisoning exact-match lookups."""
    from backend.app.terminology.translation_memory import TranslationMemory
    deleted = TranslationMemory.clear_all()
    return {"success": True, "message": f"Cleared {deleted} Translation Memory entries.", "deleted_count": deleted}

@router.delete("/{term_id}")
def delete_glossary_term(term_id: str):
    success = TerminologyManager.delete_term(term_id)
    if not success:
        raise HTTPException(status_code=404, detail="Term not found")
    return {"success": True}

@router.get("/export-csv")
def export_glossary_csv(project_id: Optional[str] = None):
    csv_str = TerminologyManager.export_csv(project_id)
    return PlainTextResponse(content=csv_str, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tarjuman_glossary.csv"})

@router.post("/import-csv")
async def import_glossary_csv(file: UploadFile = File(...), project_id: Optional[str] = None):
    content = await file.read()
    csv_text = content.decode("utf-8-sig")
    count = TerminologyManager.import_csv(csv_text, project_id)
    return {"success": True, "imported_count": count}
