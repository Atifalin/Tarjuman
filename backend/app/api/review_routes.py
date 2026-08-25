import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.database.connection import get_db
from backend.app.database.models import ChunkRecord
from backend.app.terminology.translation_memory import TranslationMemory
from backend.app.providers.router import TranslationRouter
from backend.app.providers.gemini_provider import GeminiProvider

router = APIRouter(prefix="/api/review", tags=["Review Workstation"])

class ApproveRequest(BaseModel):
    chunk_id: str
    final_urdu: str
    save_to_tm: bool = True

class EditRequest(BaseModel):
    chunk_id: str
    edited_urdu: str
    save_to_tm: bool = True

class RegenerateRequest(BaseModel):
    chunk_id: str
    model_id: Optional[str] = None

class GeminiReviewRequest(BaseModel):
    chunk_id: str
    model_id: str = "gemini-2.5-flash"

def parse_chunk_row(row) -> Dict[str, Any]:
    d = dict(row)
    if isinstance(d.get("qa_issues"), str):
        try:
            d["qa_issues"] = json.loads(d["qa_issues"])
        except Exception:
            d["qa_issues"] = []
    return d

@router.get("/{project_id}/next")
def get_next_chunk_for_review(project_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        # Find next chunk awaiting review or flagged
        cursor.execute("""
        SELECT * FROM chunks 
        WHERE project_id = ? AND status = 'awaiting_review'
        ORDER BY document_id ASC, page_number ASC, chunk_index ASC
        LIMIT 1;
        """, (project_id,))
        row = cursor.fetchone()
        if not row:
            # Check if any failed, translating, or pending
            cursor.execute("""
            SELECT * FROM chunks 
            WHERE project_id = ? AND status IN ('failed', 'translating', 'pending')
            ORDER BY document_id ASC, page_number ASC, chunk_index ASC
            LIMIT 1;
            """, (project_id,))
            row = cursor.fetchone()
            
        if not row:
            return {"chunk": None, "message": "No chunks awaiting review."}
            
        return {"chunk": parse_chunk_row(row)}

@router.get("/{project_id}/chunk/{chunk_id}")
def get_chunk_by_id(project_id: str, chunk_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ? AND project_id = ?;", (chunk_id, project_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chunk not found")
        return {"chunk": parse_chunk_row(row)}

@router.get("/{project_id}/chunks")
def list_chunks(
    project_id: str,
    status: Optional[str] = None,
    document_id: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    offset = (page - 1) * limit
    with get_db() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM chunks WHERE project_id = ?"
        params = [project_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if document_id:
            query += " AND document_id = ?"
            params.append(document_id)
            
        query += " ORDER BY document_id ASC, page_number ASC, chunk_index ASC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [parse_chunk_row(r) for r in rows]

@router.post("/{project_id}/reset-status")
def reset_project_chunks_status(project_id: str, target_status: str = "awaiting_review"):
    """Resets all chunks in a project to 'awaiting_review' or 'pending' for re-reviewing or re-translating."""
    now_str = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE chunks SET status = ?, updated_at = ? WHERE project_id = ?;",
            (target_status, now_str, project_id)
        )
    return {"success": True, "message": f"All chunks reset to {target_status}."}

@router.post("/approve")
def approve_chunk(req: ApproveRequest):
    now_str = datetime.now().isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT source_text, primary_provider, primary_model FROM chunks WHERE id = ?;", (req.chunk_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Chunk not found")
        source_text = row["source_text"]
        source_provider = row["primary_provider"]
        source_model = row["primary_model"]

        conn.execute("""
        UPDATE chunks SET
            final_urdu = ?,
            status = 'approved',
            approved_by = 'human',
            approved_at = ?,
            updated_at = ?
        WHERE id = ?;
        """, (req.final_urdu, now_str, now_str, req.chunk_id))

    if req.save_to_tm and req.final_urdu.strip():
        TranslationMemory.save_approved_translation(source_text, req.final_urdu.strip(), source_provider, source_model)

    return {"success": True, "message": "Chunk approved and saved to Translation Memory."}

@router.post("/reject")
def reject_chunk(chunk_id: str):
    now_str = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
        UPDATE chunks SET
            status = 'rejected',
            updated_at = ?
        WHERE id = ?;
        """, (now_str, chunk_id))
    return {"success": True, "message": "Chunk marked as rejected."}

class FetchEnglishReferenceRequest(BaseModel):
    chunk_id: str
    provider_model_id: str = "qwen3:8b"

@router.post("/fetch-english-reference")
async def fetch_english_reference_for_chunk(req: FetchEnglishReferenceRequest):
    """Generates an English reference bridge on demand for the current chunk."""
    router_engine = TranslationRouter()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        chunk = cursor.fetchone()
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (chunk["project_id"],))
        proj = cursor.fetchone()
        privacy_mode = proj["privacy_mode"] if proj else "LOCAL_ONLY"

    res = await router_engine.generate_english_reference(
        source_arabic=chunk["source_text"],
        provider_model_id=req.provider_model_id,
        privacy_mode=privacy_mode
    )

    now_str = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
        UPDATE chunks SET
            english_reference = ?,
            english_reference_provider = ?,
            english_reference_model = ?,
            english_reference_route = ?,
            english_reference_timestamp = ?,
            updated_at = ?
        WHERE id = ?;
        """, (
            res["english_reference"],
            res["provider"],
            res["model"],
            res["route"],
            now_str,
            now_str,
            req.chunk_id
        ))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        updated = cursor.fetchone()
        return {"success": True, "chunk": parse_chunk_row(updated)}

@router.post("/regenerate")
async def regenerate_chunk(req: RegenerateRequest):
    router_engine = TranslationRouter()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        chunk = cursor.fetchone()
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")

        cursor.execute("SELECT * FROM projects WHERE id = ?;", (chunk["project_id"],))
        proj = cursor.fetchone()

    model_to_use = req.model_id or proj["primary_model_id"]
    privacy_mode = proj["privacy_mode"] if proj and "privacy_mode" in proj.keys() else "LOCAL_ONLY"
    prod_policy = proj["production_policy"] if proj and "production_policy" in proj.keys() else "BALANCED"

    # Re-run translation
    try:
        t_res = await router_engine.route_translation(
            source_arabic=chunk["source_text"],
            routing_strategy=proj["routing_strategy"],
            production_policy=prod_policy,
            privacy_mode=privacy_mode,
            primary_model_id=model_to_use,
            secondary_model_id=proj["secondary_model_id"],
            reviewer_model_id=proj["reviewer_model_id"],
            gemini_model_id=proj["gemini_model_id"] or "gemini-3.6-flash",
            project_id=chunk["project_id"],
            bypass_tm=True
        )
    except Exception as e:
        err_msg = str(e)
        with get_db() as conn:
            conn.execute("""
            UPDATE chunks SET
                status = 'failed',
                qa_status = 'FAILED',
                qa_issues = ?,
                updated_at = ?
            WHERE id = ?;
            """, (json.dumps([err_msg], ensure_ascii=False), datetime.now().isoformat(), req.chunk_id))
        raise HTTPException(status_code=400, detail=err_msg)

    now_str = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
        UPDATE chunks SET
            target_urdu = ?,
            secondary_urdu = ?,
            reviewer_urdu = ?,
            final_urdu = ?,
            status = 'awaiting_review',
            qa_status = ?,
            qa_issues = ?,
            primary_provider = ?,
            primary_provider_class = ?,
            primary_model = ?,
            execution_backend = ?,
            route = ?,
            is_pivot = ?,
            pivot_languages = ?,
            latency_ms = ?,
            peak_ram_mb = ?,
            memory_pressure = ?,
            updated_at = ?
        WHERE id = ?;
        """, (
            t_res["target_urdu"],
            t_res["secondary_urdu"],
            t_res["reviewer_urdu"],
            t_res["final_urdu"],
            t_res["qa_status"],
            json.dumps(t_res["qa_issues"], ensure_ascii=False),
            t_res["primary_provider"],
            t_res.get("primary_provider_class"),
            t_res["primary_model"],
            t_res.get("execution_backend"),
            t_res.get("route"),
            1 if t_res.get("is_pivot") else 0,
            json.dumps(t_res.get("pivot_languages", []), ensure_ascii=False),
            t_res["latency_ms"],
            t_res.get("peak_ram_mb", 0.0),
            t_res.get("memory_pressure", "GREEN"),
            now_str,
            req.chunk_id
        ))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        updated = cursor.fetchone()
        return {"success": True, "chunk": parse_chunk_row(updated)}

@router.post("/gemini-review")
async def trigger_gemini_review_for_chunk(req: GeminiReviewRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        chunk = cursor.fetchone()
        if not chunk:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (chunk["project_id"],))
        proj = cursor.fetchone()
        if proj and proj.get("privacy_mode") == "LOCAL_ONLY":
            raise HTTPException(status_code=400, detail="Gemini Review blocked: Project privacy mode is LOCAL_ONLY.")

    gemini = GeminiProvider()
    try:
        res = await gemini.review_translation(
            source_arabic=chunk["source_text"],
            candidate_urdu=chunk["final_urdu"] or chunk["target_urdu"] or "",
            model=req.model_id or "gemini-3.6-flash"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    now_str = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
        UPDATE chunks SET
            reviewer_urdu = ?,
            final_urdu = ?,
            qa_status = ?,
            review_provider = 'gemini',
            review_model = ?,
            updated_at = ?
        WHERE id = ?;
        """, (
            res.revised_urdu,
            res.revised_urdu,
            res.qa_verdict,
            req.model_id,
            now_str,
            req.chunk_id
        ))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?;", (req.chunk_id,))
        updated = cursor.fetchone()
        return {"success": True, "chunk": parse_chunk_row(updated)}

