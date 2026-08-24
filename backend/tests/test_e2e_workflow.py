import os
import json
import pytest
from backend.app.database.connection import init_db, get_db
from backend.app.workers.orchestrator import TranslationOrchestrator
from backend.app.export.exporter import DocumentExporter
from backend.app.pdf.extractor import PDFExtractor
from backend.app.pdf.chunker import ArabicChunker

@pytest.mark.asyncio
async def test_end_to_end_ingest_and_export():
    init_db()
    from data.generate_sample_pdf import generate_sample_arabic_books
    sample_dir = os.path.abspath("data/test_sample_books")
    generate_sample_arabic_books(output_dir=sample_dir)
    
    proj_id = "test_project_e2e"
    
    # Clean any prior test project
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?;", (proj_id,))
        conn.execute("""
        INSERT INTO projects (id, name, folder_path, mode, routing_strategy, primary_model_id, created_at, updated_at)
        VALUES (?, 'Test Ingestion Project', ?, 'review', 'local_only', 'madlad400-7b-mt', '2026-01-01', '2026-01-01');
        """, (proj_id, sample_dir))

    # Ingest the folder
    await TranslationOrchestrator.ingest_project_folder(proj_id, sample_dir)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents WHERE project_id = ?;", (proj_id,))
        doc_count = cursor.fetchone()[0]
        assert doc_count >= 2

        cursor.execute("SELECT COUNT(*) FROM chunks WHERE project_id = ?;", (proj_id,))
        chunk_count = cursor.fetchone()[0]
        assert chunk_count >= 2

        # Simulate approving one chunk with translation
        cursor.execute("SELECT id, source_text FROM chunks WHERE project_id = ? LIMIT 1;", (proj_id,))
        row = cursor.fetchone()
        chunk_id = row["id"]
        source = row["source_text"]

        conn.execute("""
        UPDATE chunks SET
            target_urdu = 'یہ ایک آزمائشی اردو ترجمہ ہے جو دستاویز کی تصدیق کرتا ہے۔',
            final_urdu = 'یہ ایک آزمائشی اردو ترجمہ ہے جو دستاویز کی تصدیق کرتا ہے۔',
            status = 'approved',
            approved_by = 'human',
            qa_status = 'PASS',
            primary_model = 'madlad400-7b-mt'
        WHERE id = ?;
        """, (chunk_id,))

    # Test DOCX Export
    docx_stream = DocumentExporter.export_project_to_docx(proj_id)
    assert docx_stream.getbuffer().nbytes > 1000

    # Test JSON Export
    json_data = DocumentExporter.export_project_to_json(proj_id)
    parsed = json.loads(json_data)
    assert parsed["id"] == proj_id
    assert len(parsed["documents"]) >= 2

    # Test TXT Export
    txt_data = DocumentExporter.export_project_to_txt(proj_id, bilingual=True)
    assert "DOCUMENT:" in txt_data
    assert "ARABIC:" in txt_data

    # Test Project Start & Pause Endpoints
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    start_res = client.post(f"/api/projects/{proj_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["success"] is True

    pause_res = client.post(f"/api/projects/{proj_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["success"] is True
