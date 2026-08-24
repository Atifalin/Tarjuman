import os
import pymupdf
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.database.connection import get_db

logger = logging.getLogger(__name__)

class PDFRenderer:
    """
    Dedicated PDF Rendering & Typesetting Engine for Tarjuman.
    Supports Mode A (Urdu), Mode B (Bilingual), Mode C (Trilingual), and Mode D (Review).
    Embeds native Arabic/Urdu Unicode fonts to prevent question mark glyph corruption.
    """

    PAGE_WIDTH = 595.0   # Standard A4 width in points
    PAGE_HEIGHT = 842.0  # Standard A4 height in points
    MARGIN_X = 45.0
    MARGIN_TOP = 50.0
    MARGIN_BOTTOM = 50.0

    @classmethod
    def _get_unicode_font(cls) -> Optional[str]:
        candidates = [
            "/System/Library/Fonts/NotoNastaliq.ttc",
            "/System/Library/Fonts/GeezaPro.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/System/Library/Fonts/SFArabic.ttf",
            "/System/Library/Fonts/DecoTypeNastaleeqUrdu.ttc",
            "/System/Library/Fonts/Supplemental/Baghdad.ttc"
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    @classmethod
    def _init_page_font(cls, page: pymupdf.Page) -> str:
        font_path = cls._get_unicode_font()
        if font_path:
            try:
                page.insert_font(fontname="urdu_font", fontfile=font_path)
                return "urdu_font"
            except Exception as e:
                logger.warning(f"Failed to register custom font {font_path}: {e}")
        return "helv"

    @classmethod
    def render_urdu_pdf(
        cls,
        project_id: str,
        output_path: str,
        include_provenance: bool = False
    ) -> str:
        """
        MODE A: Clean Typeset Urdu PDF.
        Preserves source page sequences, headers, footers, and source page references.
        """
        chunks, project_name = cls._fetch_approved_chunks(project_id)
        if not chunks:
            raise RuntimeError("Cannot export PDF: No chunks found for this project.")

        doc = pymupdf.open()
        current_page = None
        current_y = cls.MARGIN_TOP
        fontname = "helv"

        # Group chunks by source page number
        chunks_by_page = {}
        for c in chunks:
            p_num = c["page_number"]
            chunks_by_page.setdefault(p_num, []).append(c)

        for source_page_num in sorted(chunks_by_page.keys()):
            page_chunks = chunks_by_page[source_page_num]
            current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
            fontname = cls._init_page_font(current_page)
            current_y = cls.MARGIN_TOP

            # Header: Project Name & Source Page Reference
            cls._draw_header(current_page, project_name, f"Source Page {source_page_num}")
            current_y += 35.0

            for chunk in page_chunks:
                urdu_text = chunk["final_urdu"] or chunk["target_urdu"] or ""
                if not urdu_text:
                    continue

                # Estimate height needed
                lines = max(1, len(urdu_text) // 55)
                box_height = max(40.0, lines * 18.0 + 20.0)

                # Check if we need a new page
                if current_y + box_height > (cls.PAGE_HEIGHT - cls.MARGIN_BOTTOM):
                    cls._draw_footer(current_page, doc.page_count)
                    current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
                    fontname = cls._init_page_font(current_page)
                    cls._draw_header(current_page, project_name, f"Source Page {source_page_num} (Cont.)")
                    current_y = cls.MARGIN_TOP + 35.0

                # Draw Urdu passage with Unicode font
                rect = pymupdf.Rect(cls.MARGIN_X, current_y, cls.PAGE_WIDTH - cls.MARGIN_X, current_y + box_height)
                current_page.insert_textbox(rect, urdu_text, fontname=fontname, fontsize=11, align=pymupdf.TEXT_ALIGN_RIGHT)
                current_y += box_height + 12.0

            cls._draw_footer(current_page, doc.page_count)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()

        cls.validate_pdf_output(output_path)
        return output_path

    @classmethod
    def render_bilingual_pdf(
        cls,
        project_id: str,
        output_path: str,
        layout: str = "stacked"  # "stacked" or "side_by_side"
    ) -> str:
        """
        MODE B: Bilingual Arabic + Urdu PDF.
        """
        chunks, project_name = cls._fetch_approved_chunks(project_id)
        if not chunks:
            raise RuntimeError("Cannot export Bilingual PDF: No chunks found.")

        doc = pymupdf.open()
        current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
        fontname = cls._init_page_font(current_page)
        current_y = cls.MARGIN_TOP + 30.0
        cls._draw_header(current_page, f"{project_name} — Bilingual Edition", "Arabic / Urdu")

        for chunk in chunks:
            arabic_text = chunk["source_text"] or ""
            urdu_text = chunk["final_urdu"] or chunk["target_urdu"] or ""

            if layout == "side_by_side":
                col_width = (cls.PAGE_WIDTH - 2 * cls.MARGIN_X - 15.0) / 2.0
                est_height = max(50.0, max(len(arabic_text), len(urdu_text)) // 30 * 16.0 + 25.0)

                if current_y + est_height > (cls.PAGE_HEIGHT - cls.MARGIN_BOTTOM):
                    cls._draw_footer(current_page, doc.page_count)
                    current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
                    fontname = cls._init_page_font(current_page)
                    cls._draw_header(current_page, f"{project_name} — Bilingual", "Arabic / Urdu")
                    current_y = cls.MARGIN_TOP + 30.0

                # Left Col: Arabic Source
                rect_ar = pymupdf.Rect(cls.MARGIN_X, current_y, cls.MARGIN_X + col_width, current_y + est_height)
                current_page.draw_rect(rect_ar, color=(0.85, 0.88, 0.92), width=0.5)
                current_page.insert_textbox(rect_ar, f"[Arabic Page {chunk['page_number']}]\n{arabic_text}", fontname=fontname, fontsize=10, align=pymupdf.TEXT_ALIGN_RIGHT)

                # Right Col: Urdu Translation
                rect_ur = pymupdf.Rect(cls.MARGIN_X + col_width + 15.0, current_y, cls.PAGE_WIDTH - cls.MARGIN_X, current_y + est_height)
                current_page.draw_rect(rect_ur, color=(0.88, 0.92, 0.88), width=0.5)
                current_page.insert_textbox(rect_ur, f"[اردو ترجمہ]\n{urdu_text}", fontname=fontname, fontsize=10, align=pymupdf.TEXT_ALIGN_RIGHT)

                current_y += est_height + 15.0

            else:
                # Stacked Layout
                ar_lines = max(1, len(arabic_text) // 55)
                ur_lines = max(1, len(urdu_text) // 55)
                block_height = (ar_lines + ur_lines) * 16.0 + 35.0

                if current_y + block_height > (cls.PAGE_HEIGHT - cls.MARGIN_BOTTOM):
                    cls._draw_footer(current_page, doc.page_count)
                    current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
                    fontname = cls._init_page_font(current_page)
                    cls._draw_header(current_page, f"{project_name} — Bilingual", "Arabic / Urdu")
                    current_y = cls.MARGIN_TOP + 30.0

                rect_block = pymupdf.Rect(cls.MARGIN_X, current_y, cls.PAGE_WIDTH - cls.MARGIN_X, current_y + block_height)
                current_page.draw_rect(rect_block, color=(0.85, 0.85, 0.85), width=0.5)

                # Arabic Top
                ar_rect = pymupdf.Rect(cls.MARGIN_X + 5, current_y + 4, cls.PAGE_WIDTH - cls.MARGIN_X - 5, current_y + ar_lines * 16.0 + 12.0)
                current_page.insert_textbox(ar_rect, f"📖 [أصل النص العربي - ص {chunk['page_number']}]\n{arabic_text}", fontname=fontname, fontsize=10, align=pymupdf.TEXT_ALIGN_RIGHT)

                # Urdu Bottom
                ur_y_start = current_y + ar_lines * 16.0 + 15.0
                ur_rect = pymupdf.Rect(cls.MARGIN_X + 5, ur_y_start, cls.PAGE_WIDTH - cls.MARGIN_X - 5, current_y + block_height - 4)
                current_page.insert_textbox(ur_rect, f"✍️ [اردو ترجمہ]\n{urdu_text}", fontname=fontname, fontsize=10, align=pymupdf.TEXT_ALIGN_RIGHT)

                current_y += block_height + 12.0

        cls._draw_footer(current_page, doc.page_count)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()

        cls.validate_pdf_output(output_path)
        return output_path

    @classmethod
    def render_trilingual_pdf(
        cls,
        project_id: str,
        output_path: str
    ) -> str:
        """
        MODE C: Trilingual PDF (Arabic Source | English Reference | Urdu Translation).
        """
        chunks, project_name = cls._fetch_approved_chunks(project_id)
        if not chunks:
            raise RuntimeError("Cannot export Trilingual PDF: No chunks found.")

        doc = pymupdf.open()
        current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
        fontname = cls._init_page_font(current_page)
        current_y = cls.MARGIN_TOP + 30.0
        cls._draw_header(current_page, f"{project_name} — Trilingual Edition", "Arabic / English / Urdu")

        for chunk in chunks:
            ar_text = chunk["source_text"] or ""
            en_text = chunk["english_reference"] or "[No English Reference]"
            ur_text = chunk["final_urdu"] or chunk["target_urdu"] or ""

            block_h = 135.0
            if current_y + block_h > (cls.PAGE_HEIGHT - cls.MARGIN_BOTTOM):
                cls._draw_footer(current_page, doc.page_count)
                current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
                fontname = cls._init_page_font(current_page)
                cls._draw_header(current_page, f"{project_name} — Trilingual", "Arabic / English / Urdu")
                current_y = cls.MARGIN_TOP + 30.0

            rect = pymupdf.Rect(cls.MARGIN_X, current_y, cls.PAGE_WIDTH - cls.MARGIN_X, current_y + block_h)
            current_page.draw_rect(rect, color=(0.85, 0.85, 0.85), width=0.5)

            # Row 1: Arabic
            r_ar = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 4, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 44.0)
            current_page.insert_textbox(r_ar, f"📖 [Arabic]\n{ar_text}", fontname=fontname, fontsize=9, align=pymupdf.TEXT_ALIGN_RIGHT)

            # Row 2: English
            r_en = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 46.0, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 86.0)
            current_page.insert_textbox(r_en, f"🌐 [English Reference]\n{en_text}", fontsize=8)

            # Row 3: Urdu
            r_ur = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 88.0, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 130.0)
            current_page.insert_textbox(r_ur, f"✍️ [Urdu Translation]\n{ur_text}", fontname=fontname, fontsize=9, align=pymupdf.TEXT_ALIGN_RIGHT)

            current_y += block_h + 10.0

        cls._draw_footer(current_page, doc.page_count)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()

        cls.validate_pdf_output(output_path)
        return output_path

    @classmethod
    def render_review_pdf(
        cls,
        project_id: str,
        output_path: str
    ) -> str:
        """
        MODE D: Review Workstation Proofreading Sheet.
        """
        chunks, project_name = cls._fetch_approved_chunks(project_id)
        if not chunks:
            raise RuntimeError("Cannot export Review PDF: No chunks found.")

        doc = pymupdf.open()
        current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
        fontname = cls._init_page_font(current_page)
        current_y = cls.MARGIN_TOP + 30.0
        cls._draw_header(current_page, f"{project_name} — Quality & Provenance Review", "Proofreading Sheet")

        for chunk in chunks:
            block_h = 100.0
            if current_y + block_h > (cls.PAGE_HEIGHT - cls.MARGIN_BOTTOM):
                cls._draw_footer(current_page, doc.page_count)
                current_page = doc.new_page(width=cls.PAGE_WIDTH, height=cls.PAGE_HEIGHT)
                fontname = cls._init_page_font(current_page)
                cls._draw_header(current_page, f"{project_name} — Review", "Proofreading Sheet")
                current_y = cls.MARGIN_TOP + 30.0

            rect = pymupdf.Rect(cls.MARGIN_X, current_y, cls.PAGE_WIDTH - cls.MARGIN_X, current_y + block_h)
            current_page.draw_rect(rect, color=(0.8, 0.8, 0.8), width=0.5)

            # Metadata header
            prov_text = f"Page {chunk['page_number']} | Chunk #{chunk['chunk_index']} | Provider: {chunk['primary_provider']} ({chunk['primary_model']}) | QA: {chunk['qa_status'] or 'N/A'}"
            r_meta = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 2, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 16.0)
            current_page.insert_textbox(r_meta, prov_text, fontsize=7)

            # Arabic Source
            r_ar = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 18.0, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 54.0)
            current_page.insert_textbox(r_ar, f"Arabic: {chunk['source_text']}", fontname=fontname, fontsize=8, align=pymupdf.TEXT_ALIGN_RIGHT)

            # Urdu Translation
            u_text = chunk["final_urdu"] or chunk["target_urdu"] or "[No Translation]"
            r_ur = pymupdf.Rect(cls.MARGIN_X + 4, current_y + 56.0, cls.PAGE_WIDTH - cls.MARGIN_X - 4, current_y + 95.0)
            current_page.insert_textbox(r_ur, f"Urdu: {u_text}", fontname=fontname, fontsize=8, align=pymupdf.TEXT_ALIGN_RIGHT)

            current_y += block_h + 10.0

        cls._draw_footer(current_page, doc.page_count)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()

        cls.validate_pdf_output(output_path)
        return output_path

    @classmethod
    def validate_pdf_output(cls, pdf_path: str) -> bool:
        """
        Automated post-generation validation:
        1. Verifies file exists on disk and is non-empty.
        2. Reopens with PyMuPDF.
        3. Verifies page_count > 0.
        4. Validates text content exists on at least one page.
        """
        if not os.path.exists(pdf_path):
            raise RuntimeError(f"Export Validation Failed: File not created at {pdf_path}")

        file_size = os.path.getsize(pdf_path)
        if file_size < 100:
            raise RuntimeError(f"Export Validation Failed: PDF file size is suspiciously small ({file_size} bytes).")

        try:
            doc = pymupdf.open(pdf_path)
            num_pages = doc.page_count
            if num_pages == 0:
                doc.close()
                raise RuntimeError("Export Validation Failed: Generated PDF contains 0 pages.")

            total_text_len = sum(len(p.get_text().strip()) for p in doc)
            doc.close()

            if total_text_len == 0:
                raise RuntimeError("Export Validation Failed: Generated PDF pages contain zero extractable text.")

            logger.info(f"PDF Validation Passed: {pdf_path} ({num_pages} pages, {file_size} bytes).")
            return True
        except Exception as e:
            logger.error(f"PDF Validation Error for {pdf_path}: {e}")
            raise RuntimeError(f"Export Validation Failed: {str(e)}")

    @classmethod
    def _fetch_approved_chunks(cls, project_id: str, approved_only: bool = False):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM projects WHERE id = ?;", (project_id,))
            proj = cursor.fetchone()
            project_name = proj["name"] if proj else "Project"

            if approved_only:
                cursor.execute("""
                SELECT * FROM chunks 
                WHERE project_id = ? AND status = 'approved'
                ORDER BY page_number ASC, chunk_index ASC;
                """, (project_id,))
            else:
                cursor.execute("""
                SELECT * FROM chunks 
                WHERE project_id = ?
                ORDER BY page_number ASC, chunk_index ASC;
                """, (project_id,))
            
            chunks = cursor.fetchall()
            return [dict(c) for c in chunks], project_name

    @classmethod
    def _draw_header(cls, page, title: str, subtitle: str):
        rect = pymupdf.Rect(cls.MARGIN_X, 20.0, cls.PAGE_WIDTH - cls.MARGIN_X, 45.0)
        page.insert_textbox(rect, f"{title} | {subtitle}", fontsize=8, color=(0.4, 0.4, 0.4))
        page.draw_line(pymupdf.Point(cls.MARGIN_X, 48.0), pymupdf.Point(cls.PAGE_WIDTH - cls.MARGIN_X, 48.0), color=(0.8, 0.8, 0.8), width=0.5)

    @classmethod
    def _draw_footer(cls, page, page_num: int):
        y = cls.PAGE_HEIGHT - 30.0
        page.draw_line(pymupdf.Point(cls.MARGIN_X, y - 5.0), pymupdf.Point(cls.PAGE_WIDTH - cls.MARGIN_X, y - 5.0), color=(0.8, 0.8, 0.8), width=0.5)
        page.insert_text(pymupdf.Point(cls.PAGE_WIDTH / 2.0 - 15.0, y + 10.0), f"— {page_num} —", fontsize=8, color=(0.4, 0.4, 0.4))
