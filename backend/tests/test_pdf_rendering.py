import os
import tempfile
import pymupdf
from backend.app.database.connection import init_db, get_db
from backend.app.pdf.pdf_renderer import PDFRenderer

def test_pdf_renderer_all_modes():
    init_db()
    temp_dir = tempfile.gettempdir()
    project_id = "test_pdf_proj_001"

    # Seed test project and chunks
    with get_db() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
        conn.execute("DELETE FROM chunks WHERE project_id = ?;", (project_id,))
        
        conn.execute("""
        INSERT INTO projects (id, name, folder_path, mode, routing_strategy, primary_model_id, created_at, updated_at)
        VALUES (?, 'Kitab at-Tawheed', '/dummy/path', 'review', 'local_only', 'madlad400-7b-mt', '2026-08-24T00:00:00', '2026-08-24T00:00:00');
        """, (project_id,))

        conn.execute("""
        INSERT INTO documents (id, project_id, filename, filepath, total_pages, processed_pages, total_chunks, completed_chunks, is_scanned, status)
        VALUES ('doc_001', ?, 'tawheed.pdf', '/dummy/tawheed.pdf', 1, 1, 1, 1, 0, 'completed');
        """, (project_id,))

        conn.execute("""
        INSERT INTO chunks (
            id, document_id, project_id, page_number, chunk_index, source_text, target_urdu, final_urdu, english_reference, status, qa_status, primary_provider, primary_model, route, is_pivot, created_at, updated_at
        ) VALUES (
            'chk_001', 'doc_001', ?, 1, 0,
            'بسم الله الرحمن الرحيم. الحمد لله رب العالمين وصلى الله وسلم على نبينا محمد وعلى آله وصحبه أجمعين.',
            'شروع اللہ کے نام سے جو بڑا مہربان نہایت رحم والا ہے۔ تمام تعریفیں اللہ کے لیے ہیں جو تمام جہانوں کا پالنے والا ہے۔',
            'شروع اللہ کے نام سے جو بڑا مہربان نہایت رحم والا ہے۔ تمام تعریفیں اللہ کے لیے ہیں جو تمام جہانوں کا پالنے والا ہے۔',
            'In the name of Allah, the Most Gracious, the Most Merciful. Praise be to Allah, the Lord of all creation.',
            'approved', 'PASS', 'Argos', 'argos-translate', 'ar -> en -> ur', 1,
            '2026-08-24T00:00:00', '2026-08-24T00:00:00'
        );
        """, (project_id,))

    # Test Mode A: Urdu PDF
    urdu_pdf = os.path.join(temp_dir, "test_mode_a_urdu.pdf")
    PDFRenderer.render_urdu_pdf(project_id, urdu_pdf)
    assert os.path.exists(urdu_pdf)
    doc_a = pymupdf.open(urdu_pdf)
    assert doc_a.page_count >= 1
    doc_a.close()

    # Test Mode B: Bilingual PDF (Stacked & Side-by-Side)
    bilingual_stacked = os.path.join(temp_dir, "test_mode_b_stacked.pdf")
    PDFRenderer.render_bilingual_pdf(project_id, bilingual_stacked, layout="stacked")
    assert os.path.exists(bilingual_stacked)
    doc_b1 = pymupdf.open(bilingual_stacked)
    assert doc_b1.page_count >= 1
    doc_b1.close()

    bilingual_sbs = os.path.join(temp_dir, "test_mode_b_sbs.pdf")
    PDFRenderer.render_bilingual_pdf(project_id, bilingual_sbs, layout="side_by_side")
    assert os.path.exists(bilingual_sbs)
    doc_b2 = pymupdf.open(bilingual_sbs)
    assert doc_b2.page_count >= 1
    doc_b2.close()

    # Test Mode C: Trilingual PDF
    trilingual_pdf = os.path.join(temp_dir, "test_mode_c_trilingual.pdf")
    PDFRenderer.render_trilingual_pdf(project_id, trilingual_pdf)
    assert os.path.exists(trilingual_pdf)
    doc_c = pymupdf.open(trilingual_pdf)
    assert doc_c.page_count >= 1
    doc_c.close()

    # Test Mode D: Review PDF
    review_pdf = os.path.join(temp_dir, "test_mode_d_review.pdf")
    PDFRenderer.render_review_pdf(project_id, review_pdf)
    assert os.path.exists(review_pdf)
    doc_d = pymupdf.open(review_pdf)
    assert doc_d.page_count >= 1
    doc_d.close()
