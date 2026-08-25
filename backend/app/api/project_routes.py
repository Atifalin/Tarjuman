import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from backend.app.database.connection import get_db
from backend.app.database.models import ProjectCreate, ProjectRecord, DocumentRecord
from backend.app.workers.orchestrator import TranslationOrchestrator

router = APIRouter(prefix="/api/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectRecord])
def list_projects():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        return [ProjectRecord(**dict(r)) for r in rows]

@router.post("", response_model=ProjectRecord)
async def create_project(req: ProjectCreate, background_tasks: BackgroundTasks):
    if not os.path.exists(req.folder_path):
        raise HTTPException(status_code=400, detail=f"Folder path does not exist: {req.folder_path}")

    proj_id = str(uuid.uuid4())
    now_str = datetime.now().isoformat()

    with get_db() as conn:
        conn.execute("""
        INSERT INTO projects (
            id, name, folder_path, mode, routing_strategy,
            primary_model_id, secondary_model_id, reviewer_model_id,
            gemini_model_id, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?);
        """, (
            proj_id, req.name, req.folder_path, req.mode, req.routing_strategy,
            req.primary_model_id, req.secondary_model_id, req.reviewer_model_id,
            req.gemini_model_id, now_str, now_str
        ))

    # Scan and ingest PDF files in background
    background_tasks.add_task(TranslationOrchestrator.ingest_project_folder, proj_id, req.folder_path)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (proj_id,))
        row = cursor.fetchone()
        return ProjectRecord(**dict(row))

class ProjectModelUpdate(BaseModel):
    primary_model_id: Optional[str] = None
    secondary_model_id: Optional[str] = None
    reviewer_model_id: Optional[str] = None
    gemini_model_id: Optional[str] = None
    mode: Optional[str] = None  # review, automatic, hybrid

@router.patch("/{project_id}/models")
def update_project_models(project_id: str, req: ProjectModelUpdate):
    """Updates the translation engine configuration (and optionally the processing mode)
    for an existing project — e.g. switch away from a heavy model that was never
    downloaded, or switch out of 'review' mode (which intentionally stops after every
    single chunk to wait for human approval) into 'hybrid' mode for continuous queue
    processing — without recreating the project."""
    updates = {k: (None if v == "" else v) for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No model fields provided to update.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?;", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [datetime.now().isoformat(), project_id]
        conn.execute(f"UPDATE projects SET {set_clause}, updated_at = ? WHERE id = ?;", values)

        cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        return ProjectRecord(**dict(row))

@router.get("/{project_id}")
def get_project_details(project_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
        proj = cursor.fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get summary statistics
        cursor.execute("SELECT COUNT(*) FROM documents WHERE project_id = ?;", (project_id,))
        total_docs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ?;", (project_id,))
        total_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ? AND status = 'approved';", (project_id,))
        approved_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ? AND status = 'awaiting_review';", (project_id,))
        awaiting_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ? AND status = 'failed';", (project_id,))
        failed_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ? AND status = 'translating';", (project_id,))
        translating_chunks = cursor.fetchone()[0]

        translated_chunks = approved_chunks + awaiting_chunks
        translation_progress = round((translated_chunks / max(total_chunks, 1)) * 100, 1)
        review_progress = round((approved_chunks / max(total_chunks, 1)) * 100, 1)
        is_running = TranslationOrchestrator.is_project_running(project_id)

        return {
            "project": dict(proj),
            "stats": {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "translated_chunks": translated_chunks,
                "approved_chunks": approved_chunks,
                "awaiting_review_chunks": awaiting_chunks,
                "translating_chunks": translating_chunks,
                "failed_chunks": failed_chunks,
                "translation_progress": translation_progress,
                "review_progress": review_progress,
                "progress_percentage": translation_progress,
                "is_running": is_running
            }
        }

@router.get("/{project_id}/documents")
def list_project_documents(project_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE project_id = ? ORDER BY filename ASC;", (project_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

@router.get("/{project_id}/documents/{document_id}/transcript")
def get_document_transcript(project_id: str, document_id: str):
    """
    Returns the raw OCR/extracted Arabic source text for every chunk of a document, in
    page/chunk order, along with which OCR engine produced each chunk. Lets a user grab
    just the transcription (e.g. Qari-OCR output) without needing to run translation.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM documents WHERE id = ? AND project_id = ?;", (document_id, project_id))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        cursor.execute("""
        SELECT page_number, chunk_index, source_text, ocr_engine, ocr_timestamp
        FROM chunks WHERE document_id = ?
        ORDER BY page_number ASC, chunk_index ASC;
        """, (document_id,))
        rows = [dict(r) for r in cursor.fetchall()]

        engines_used = sorted({r["ocr_engine"] for r in rows if r["ocr_engine"]})
        full_text = "\n\n".join(r["source_text"] for r in rows if r["source_text"])

        return {
            "document_id": document_id,
            "filename": doc["filename"],
            "chunks": rows,
            "full_text": full_text,
            "ocr_engines_used": engines_used
        }

@router.get("/{project_id}/documents/{document_id}/transcript.txt")
def download_document_transcript(project_id: str, document_id: str):
    from fastapi.responses import PlainTextResponse
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM documents WHERE id = ? AND project_id = ?;", (document_id, project_id))
        doc = cursor.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        cursor.execute("""
        SELECT source_text FROM chunks WHERE document_id = ?
        ORDER BY page_number ASC, chunk_index ASC;
        """, (document_id,))
        full_text = "\n\n".join(r["source_text"] for r in cursor.fetchall() if r["source_text"])

    base_name = os.path.splitext(doc["filename"])[0]
    return PlainTextResponse(
        content=full_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{base_name}_transcript.txt"'}
    )

@router.post("/{project_id}/start")
async def start_project_processing(project_id: str):
    TranslationOrchestrator.start_project(project_id)
    return {"success": True, "message": "Translation queue started."}

@router.post("/{project_id}/pause")
async def pause_project_processing(project_id: str):
    TranslationOrchestrator.pause_project(project_id)
    return {"success": True, "message": "Translation queue paused."}

@router.post("/{project_id}/rescan")
async def rescan_project_folder(project_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        folder_path = row["folder_path"]

    await TranslationOrchestrator.ingest_project_folder(project_id, folder_path)
    return {"success": True, "message": "Project folder rescanned successfully."}

@router.post("/{project_id}/upload-pdf")
async def upload_pdf_files(
    project_id: str,
    files: List[UploadFile] = File(...)
):
    """
    Accepts dragged & dropped or uploaded PDF files, saves them into the project folder,
    and immediately parses and ingests them into the document/chunk queue.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT folder_path FROM projects WHERE id = ?;", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        folder_path = row["folder_path"]

    # Ensure each project has its own isolated upload directory
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads", project_id))
    os.makedirs(upload_dir, exist_ok=True)

    with get_db() as conn:
        conn.execute("UPDATE projects SET folder_path = ? WHERE id = ?;", (upload_dir, project_id))

    saved_files = []
    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            continue
        dest_path = os.path.join(upload_dir, upload.filename)
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved_files.append(upload.filename)

    # Ingest only the project's dedicated folder
    await TranslationOrchestrator.ingest_project_folder(project_id, upload_dir)

    # Return refreshed documents
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE project_id = ? ORDER BY filename ASC;", (project_id,))
        docs = cursor.fetchall()
        return {
            "success": True,
            "uploaded": saved_files,
            "documents": [dict(d) for d in docs]
        }

@router.delete("/{project_id}/documents/{document_id}")
async def delete_document(project_id: str, document_id: str):
    """Deletes a specific document and all its chunks from the queue and physical disk."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filepath FROM documents WHERE id = ? AND project_id = ?;", (document_id, project_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        
        filepath = row["filepath"]
        cursor.execute("DELETE FROM chunks WHERE document_id = ?;", (document_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?;", (document_id,))
    
    # Delete physical file from disk so rescan doesn't re-add it
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f"Failed deleting physical file {filepath}: {e}")

    return {"success": True, "message": "Document deleted successfully."}

@router.post("/{project_id}/clear-queue")
async def clear_project_queue(project_id: str):
    """Clears all documents and chunks from the project translation queue and deletes uploaded files."""
    TranslationOrchestrator.pause_project(project_id)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filepath FROM documents WHERE project_id = ?;", (project_id,))
        docs = cursor.fetchall()
        for d in docs:
            fpath = d["filepath"]
            try:
                if fpath and os.path.exists(fpath):
                    os.remove(fpath)
            except Exception:
                pass
        conn.execute("DELETE FROM chunks WHERE project_id = ?;", (project_id,))
        conn.execute("DELETE FROM documents WHERE project_id = ?;", (project_id,))

    # Also clean project upload folder
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "uploads", project_id))
    if os.path.exists(upload_dir):
        try:
            for fname in os.listdir(upload_dir):
                fpath = os.path.join(upload_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
        except Exception:
            pass

    return {"success": True, "message": "Queue cleared successfully."}

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    TranslationOrchestrator.pause_project(project_id)
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
    return {"success": True, "message": "Project deleted."}
