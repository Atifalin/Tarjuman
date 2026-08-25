import os
import fitz
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.app.database.connection import get_db
from backend.app.pdf.extractor import PDFExtractor
from backend.app.pdf.chunker import ArabicChunker
from backend.app.pdf.ocr import OCRProvider
from backend.app.providers.router import TranslationRouter
from backend.app.hardware.memory_guard import MemorySafetyGuard

logger = logging.getLogger(__name__)

class ServerActivityTracker:
    """
    Real-time Server Process & Activity Telemetry.
    Broadcasts easy-to-understand process descriptions to the top status bar.
    """
    _state: Dict[str, Any] = {
        "status": "IDLE", # "IDLE" | "INGESTING" | "OCR_PROCESSING" | "TRANSLATING" | "REVIEWING" | "ERROR" | "COMPLETED" | "PAUSED"
        "activity_message": "Server idle — ready for translation.",
        "current_project_id": None,
        "current_file": None,
        "current_chunk": None,
        "last_error": None,
        "error_timestamp": None,
        "updated_at": datetime.now().isoformat()
    }

    @classmethod
    def set_activity(cls, status: str, message: str, project_id: Optional[str] = None, file_name: Optional[str] = None, chunk_info: Optional[str] = None):
        cls._state["status"] = status
        cls._state["activity_message"] = message
        cls._state["current_project_id"] = project_id
        cls._state["current_file"] = file_name
        cls._state["current_chunk"] = chunk_info
        cls._state["updated_at"] = datetime.now().isoformat()
        logger.info(f"[Server Activity] {status}: {message}")

    @classmethod
    def set_error(cls, error_message: str, project_id: Optional[str] = None, file_name: Optional[str] = None):
        cls._state["status"] = "ERROR"
        cls._state["activity_message"] = f"Translation Failed: {error_message}"
        cls._state["last_error"] = error_message
        cls._state["error_timestamp"] = datetime.now().isoformat()
        cls._state["current_project_id"] = project_id
        cls._state["current_file"] = file_name
        cls._state["updated_at"] = datetime.now().isoformat()
        logger.error(f"[Server Activity ERROR] {error_message}")

    @classmethod
    def clear_error(cls):
        cls._state["last_error"] = None
        cls._state["error_timestamp"] = None
        if cls._state["status"] == "ERROR":
            cls._state["status"] = "IDLE"
            cls._state["activity_message"] = "Server idle — ready for translation."

    @classmethod
    def get_state(cls) -> Dict[str, Any]:
        return dict(cls._state)

class TranslationOrchestrator:
    """
    Asynchronous Background Queue Orchestrator for Tarjuman.
    Handles multi-document batching, page preservation, memory safety throttling,
    and execution modes (Review, Automatic, Hybrid).
    """

    _running_tasks: Dict[str, asyncio.Task] = {}
    _paused_projects: set = set()

    @classmethod
    def is_project_running(cls, project_id: str) -> bool:
        task = cls._running_tasks.get(project_id)
        return task is not None and not task.done()

    @classmethod
    def pause_project(cls, project_id: str):
        cls._paused_projects.add(project_id)
        if project_id in cls._running_tasks:
            cls._running_tasks[project_id].cancel()
            del cls._running_tasks[project_id]
        with get_db() as conn:
            conn.execute("UPDATE projects SET status = 'paused', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), project_id))
        ServerActivityTracker.set_activity("PAUSED", "Translation queue paused by user.", project_id)

    @classmethod
    async def ingest_project_folder(cls, project_id: str, folder_path: str):
        """Scans folder for Arabic PDFs, prunes removed files, and extracts chunks into SQLite."""
        if not os.path.exists(folder_path):
            ServerActivityTracker.set_error(f"Folder path does not exist: {folder_path}", project_id)
            raise FileNotFoundError(f"Folder path does not exist: {folder_path}")

        ServerActivityTracker.set_activity("INGESTING", f"Scanning project folder ({os.path.basename(folder_path)})...", project_id)
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
        pdf_files.sort()
        present_paths = {os.path.join(folder_path, f) for f in pdf_files}

        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Prune documents that were deleted from disk
            cursor.execute("SELECT id, filepath FROM documents WHERE project_id = ?;", (project_id,))
            existing_docs = cursor.fetchall()
            for doc_row in existing_docs:
                d_id, d_path = doc_row["id"], doc_row["filepath"]
                if d_path not in present_paths or not os.path.exists(d_path):
                    cursor.execute("DELETE FROM chunks WHERE document_id = ?;", (d_id,))
                    cursor.execute("DELETE FROM documents WHERE id = ?;", (d_id,))
                    logger.info(f"Pruned removed PDF from database: {d_path}")

            # 2. Ingest newly added PDFs or re-extract documents with 0 chunks
            for fname in pdf_files:
                fpath = os.path.join(folder_path, fname)
                cursor.execute("SELECT id, total_chunks FROM documents WHERE project_id = ? AND filepath = ?;", (project_id, fpath))
                existing = cursor.fetchone()
                if existing:
                    # Check if chunks actually exist
                    cursor.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?;", (existing["id"],))
                    c_count = cursor.fetchone()[0]
                    if c_count > 0:
                        continue
                    else:
                        # Clean empty doc record to re-extract with OCR
                        cursor.execute("DELETE FROM documents WHERE id = ?;", (existing["id"],))

                try:
                    info = PDFExtractor.inspect_pdf(fpath)
                    doc_id = str(uuid.uuid4())
                    cursor.execute("""
                    INSERT INTO documents (id, project_id, filename, filepath, total_pages, is_scanned, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending');
                    """, (doc_id, project_id, fname, fpath, info["total_pages"], 1 if info["is_scanned"] else 0))

                    # Parse pages and insert chunks
                    doc = fitz.open(fpath)
                    for page_num in range(1, info["total_pages"] + 1):
                        page_text, is_scanned_page, page_type = PDFExtractor.extract_page_text(doc, page_num)
                        ocr_engine_used = None
                        
                        if is_scanned_page or not page_text:
                            from backend.app.pdf.qwen_vl_ocr import QwenVLOCRProvider
                            from backend.app.pdf.mlx_ocr_provider import MLXOCRProvider

                            mlx_avail = await MLXOCRProvider.check_availability()
                            if mlx_avail.get("is_available") and not mlx_avail.get("models"):
                                # Server is up but hasn't loaded weights into memory yet (first request only).
                                ServerActivityTracker.set_activity(
                                    "OCR_PROCESSING",
                                    f"Loading Qari-OCR-0.4.0 model into memory (first page only, ~30-90s on Apple Silicon)... {fname} (Page {page_num}/{info['total_pages']})",
                                    project_id,
                                    fname,
                                    f"Page {page_num}"
                                )
                            elif mlx_avail.get("is_available"):
                                ServerActivityTracker.set_activity(
                                    "OCR_PROCESSING",
                                    f"Transcribing with Qari-OCR-0.4.0 (MLX, native Arabic): {fname} (Page {page_num}/{info['total_pages']})...",
                                    project_id,
                                    fname,
                                    f"Page {page_num}"
                                )
                            else:
                                ServerActivityTracker.set_activity(
                                    "OCR_PROCESSING",
                                    f"Qari-OCR MLX server not running — using Qwen2-VL/Apple Vision fallback: {fname} (Page {page_num}/{info['total_pages']})...",
                                    project_id,
                                    fname,
                                    f"Page {page_num}"
                                )

                            ocr_text, ocr_ok, ocr_engine_used, is_fallback = await QwenVLOCRProvider.ocr_page(doc, page_num)
                            if ocr_ok and ocr_text:
                                page_text = ocr_text
                            ServerActivityTracker.set_activity(
                                "OCR_PROCESSING",
                                f"Finished page {page_num}/{info['total_pages']} via {ocr_engine_used} ({'fallback' if is_fallback else 'primary'}).",
                                project_id,
                                fname,
                                f"Page {page_num}"
                            )

                        page_chunks = ArabicChunker.chunk_page_text(page_text, page_num)
                        now_str = datetime.now().isoformat()
                        
                        for c in page_chunks:
                            chunk_id = str(uuid.uuid4())
                            cursor.execute("""
                            INSERT INTO chunks (
                                id, document_id, project_id, page_number, chunk_index,
                                source_text, status, ocr_engine, ocr_timestamp, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?);
                            """, (
                                chunk_id, doc_id, project_id, page_num, c["chunk_index"],
                                c["text"], ocr_engine_used, now_str if ocr_engine_used else None, now_str, now_str
                            ))

                    doc.close()
                    # Update document totals
                    cursor.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?;", (doc_id,))
                    total_c = cursor.fetchone()[0]
                    cursor.execute("UPDATE documents SET total_chunks = ? WHERE id = ?;", (total_c, doc_id))
                except Exception as e:
                    logger.error(f"Error ingesting PDF {fname}: {e}")
                    ServerActivityTracker.set_error(f"Error ingesting PDF {fname}: {e}", project_id, fname)

            ServerActivityTracker.set_activity("IDLE", f"Project folder scanned. Chunks ready for translation.", project_id)

    @classmethod
    async def run_project_queue(cls, project_id: str):
        """Starts continuous processing loop for the given project."""
        cls._paused_projects.discard(project_id)
        router = TranslationRouter()

        with get_db() as conn:
            conn.execute("UPDATE projects SET status = 'active', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), project_id))

        ServerActivityTracker.clear_error()
        ServerActivityTracker.set_activity("TRANSLATING", "Starting project translation queue...", project_id)

        while project_id not in cls._paused_projects:
            # 1. Check memory safety throttle
            throttle = MemorySafetyGuard.get_runtime_throttle_policy()
            if throttle["action"] == "PAUSE":
                msg = f"Memory safety throttling active: {throttle['reason']}. Pausing 5s..."
                ServerActivityTracker.set_activity("PAUSED", msg, project_id)
                logger.warning(msg)
                await asyncio.sleep(5)
                continue

            # 2. Fetch project settings
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM projects WHERE id = ?;", (project_id,))
                proj = cursor.fetchone()
                if not proj or proj["status"] == "paused":
                    ServerActivityTracker.set_activity("PAUSED", "Translation queue paused.", project_id)
                    break

                # 3. Fetch next pending chunk
                cursor.execute("""
                SELECT c.*, d.filename as doc_filename 
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.project_id = ? AND c.status = 'pending'
                ORDER BY c.document_id ASC, c.page_number ASC, c.chunk_index ASC
                LIMIT 1;
                """, (project_id,))
                chunk = cursor.fetchone()
                
                if not chunk:
                    # Check if any chunks failed
                    cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ? AND status = 'failed';", (project_id,))
                    failed_count = cursor.fetchone()[0]
                    if failed_count > 0:
                        ServerActivityTracker.set_activity("ERROR", f"Translation finished with {failed_count} failed chunk(s). Review errors in Workstation.", project_id)
                        conn.execute("UPDATE projects SET status = 'paused', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), project_id))
                    else:
                        ServerActivityTracker.set_activity("COMPLETED", "All chunks completed successfully and ready for review.", project_id)
                        conn.execute("UPDATE projects SET status = 'completed', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), project_id))
                    break

                chunk_id = chunk["id"]
                source_text = chunk["source_text"]
                doc_id = chunk["document_id"]
                doc_fname = chunk["doc_filename"] or "document.pdf"
                chunk_info_str = f"Page {chunk['page_number']}, Chunk #{chunk['chunk_index']}"
                
                # Mark as translating
                conn.execute("UPDATE chunks SET status = 'translating', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), chunk_id))

            # Determine active model description for UI
            strat = proj["routing_strategy"]
            active_model = proj["gemini_model_id"] if strat == "gemini_primary" else proj["primary_model_id"]
            ServerActivityTracker.set_activity(
                "TRANSLATING",
                f"Translating {chunk_info_str} ({doc_fname}) using {active_model}...",
                project_id,
                doc_fname,
                chunk_info_str
            )

            # 4. Route chunk translation through router
            try:
                t_res = await router.route_translation(
                    source_arabic=source_text,
                    routing_strategy=proj["routing_strategy"],
                    primary_model_id=proj["primary_model_id"],
                    secondary_model_id=proj["secondary_model_id"],
                    reviewer_model_id=proj["reviewer_model_id"],
                    gemini_model_id=proj["gemini_model_id"] or "gemini-3.6-flash",
                    project_id=project_id
                )

                qa_status = t_res["qa_status"]
                issues = json.dumps(t_res["qa_issues"], ensure_ascii=False)
                now_str = datetime.now().isoformat()

                # Determine next state based on Project Mode
                mode = proj["mode"]  # review, automatic, hybrid
                new_status = "awaiting_review"
                approved_by = None
                approved_at = None

                if mode == "automatic":
                    # Fully unattended
                    new_status = "approved"
                    approved_by = "auto"
                    approved_at = now_str
                elif mode == "hybrid":
                    if qa_status == "PASS":
                        new_status = "approved"
                        approved_by = "auto"
                        approved_at = now_str
                    else:
                        new_status = "awaiting_review"
                else:
                    # Review Mode pauses
                    new_status = "awaiting_review"

                with get_db() as conn:
                    conn.execute("""
                    UPDATE chunks SET
                        target_urdu = ?,
                        secondary_urdu = ?,
                        reviewer_urdu = ?,
                        final_urdu = ?,
                        status = ?,
                        qa_status = ?,
                        qa_issues = ?,
                        primary_provider = ?,
                        primary_model = ?,
                        secondary_provider = ?,
                        secondary_model = ?,
                        review_provider = ?,
                        review_model = ?,
                        approved_by = ?,
                        approved_at = ?,
                        latency_ms = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """, (
                        t_res["target_urdu"],
                        t_res["secondary_urdu"],
                        t_res["reviewer_urdu"],
                        t_res["final_urdu"],
                        new_status,
                        qa_status,
                        issues,
                        t_res["primary_provider"],
                        t_res["primary_model"],
                        t_res["secondary_provider"],
                        t_res["secondary_model"],
                        t_res["review_provider"],
                        t_res["review_model"],
                        approved_by,
                        approved_at,
                        t_res["latency_ms"],
                        now_str,
                        chunk_id
                    ))

                    # Update document completed chunk stats
                    conn.execute("""
                    UPDATE documents SET completed_chunks = (
                        SELECT COUNT(*) FROM chunks WHERE document_id = ? AND status IN ('approved', 'awaiting_review')
                    ) WHERE id = ?;
                    """, (doc_id, doc_id))

                ServerActivityTracker.set_activity(
                    "REVIEWING" if mode == "review" else "TRANSLATING",
                    f"Finished {chunk_info_str} ({doc_fname}). Status: {new_status} (QA: {qa_status})",
                    project_id,
                    doc_fname,
                    chunk_info_str
                )

                # In review mode, stop after one chunk translation to wait for user approval
                if mode == "review":
                    break

            except Exception as e:
                err_text = str(e)
                logger.error(f"Failed processing chunk {chunk_id}: {err_text}")
                ServerActivityTracker.set_error(err_text, project_id, doc_fname)
                with get_db() as conn:
                    conn.execute("""
                    UPDATE chunks SET
                        status = 'failed',
                        qa_status = 'FAILED',
                        qa_issues = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """, (json.dumps([f"Translation Error: {err_text}"], ensure_ascii=False), datetime.now().isoformat(), chunk_id))
                    conn.execute("UPDATE documents SET status = 'error', error_message = ? WHERE id = ?;", (err_text, doc_id))
                    conn.execute("UPDATE projects SET status = 'paused', updated_at = ? WHERE id = ?;", (datetime.now().isoformat(), project_id))
                # Stop processing on fatal project error
                break

            # Yield control to event loop
            await asyncio.sleep(0.05)

    @classmethod
    def start_project(cls, project_id: str):
        if cls.is_project_running(project_id):
            return
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(cls.run_project_queue(project_id))
            cls._running_tasks[project_id] = task
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                task = loop.create_task(cls.run_project_queue(project_id))
                cls._running_tasks[project_id] = task
            except Exception as e:
                logger.error(f"Failed to start orchestrator task for project {project_id}: {e}")
