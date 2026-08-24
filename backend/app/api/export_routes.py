from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, PlainTextResponse, Response, FileResponse
import tempfile
import os
from backend.app.export.exporter import DocumentExporter
from backend.app.pdf.pdf_renderer import PDFRenderer

router = APIRouter(prefix="/api/export", tags=["Export"])

@router.get("/{project_id}/pdf/urdu")
def export_project_urdu_pdf(project_id: str):
    """MODE A: Clean Typeset Urdu PDF."""
    try:
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, f"tarjuman_{project_id}_urdu.pdf")
        PDFRenderer.render_urdu_pdf(project_id, out_path)
        return FileResponse(
            out_path,
            media_type="application/pdf",
            filename=f"tarjuman_{project_id}_urdu.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/pdf/bilingual")
def export_project_bilingual_pdf(project_id: str, layout: str = Query("stacked", pattern="^(stacked|side_by_side)$")):
    """MODE B: Bilingual Arabic + Urdu PDF."""
    try:
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, f"tarjuman_{project_id}_bilingual_{layout}.pdf")
        PDFRenderer.render_bilingual_pdf(project_id, out_path, layout=layout)
        return FileResponse(
            out_path,
            media_type="application/pdf",
            filename=f"tarjuman_{project_id}_bilingual.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/pdf/trilingual")
def export_project_trilingual_pdf(project_id: str):
    """MODE C: Trilingual PDF (Arabic | English Ref | Urdu)."""
    try:
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, f"tarjuman_{project_id}_trilingual.pdf")
        PDFRenderer.render_trilingual_pdf(project_id, out_path)
        return FileResponse(
            out_path,
            media_type="application/pdf",
            filename=f"tarjuman_{project_id}_trilingual.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/pdf/review")
def export_project_review_pdf(project_id: str):
    """MODE D: Source-Aligned Review PDF."""
    try:
        temp_dir = tempfile.gettempdir()
        out_path = os.path.join(temp_dir, f"tarjuman_{project_id}_review.pdf")
        PDFRenderer.render_review_pdf(project_id, out_path)
        return FileResponse(
            out_path,
            media_type="application/pdf",
            filename=f"tarjuman_{project_id}_review.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{project_id}/docx")
def export_project_docx(project_id: str):
    buf = DocumentExporter.export_project_to_docx(project_id)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=tarjuman_{project_id}.docx"}
    )

@router.get("/{project_id}/txt")
def export_project_txt(project_id: str, bilingual: bool = False):
    txt_content = DocumentExporter.export_project_to_txt(project_id, bilingual=bilingual)
    return PlainTextResponse(
        txt_content,
        headers={"Content-Disposition": f"attachment; filename=tarjuman_{project_id}.txt"}
    )

@router.get("/{project_id}/json")
def export_project_json(project_id: str):
    json_str = DocumentExporter.export_project_to_json(project_id)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=tarjuman_{project_id}.json"}
    )
