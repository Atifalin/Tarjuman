import os
import re
import fitz  # PyMuPDF
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Unicode ranges for Arabic script (Arabic, Arabic Supplement, Extended-A, Presentation Forms)
ARABIC_PATTERN = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
LATIN_PATTERN = re.compile(r'[a-zA-Z]')

class PDFExtractor:
    """Multi-factor per-page text extractor and classifier for Arabic PDFs."""

    @staticmethod
    def analyze_text_script(text: str) -> Dict[str, Any]:
        """Analyzes text character distribution for Arabic vs Latin scripts."""
        if not text:
            return {"arabic_chars": 0, "latin_chars": 0, "total_chars": 0, "arabic_ratio": 0.0, "latin_ratio": 0.0, "primary_script": "empty"}

        arabic_matches = ARABIC_PATTERN.findall(text)
        latin_matches = LATIN_PATTERN.findall(text)
        
        non_space_chars = len(re.sub(r'\s+', '', text))
        total = max(non_space_chars, 1)

        ar_count = len(arabic_matches)
        lat_count = len(latin_matches)

        ar_ratio = ar_count / total
        lat_ratio = lat_count / total

        if ar_ratio >= 0.40:
            primary = "arabic"
        elif lat_ratio >= 0.50:
            primary = "latin"
        else:
            primary = "mixed" if (ar_count + lat_count) > 10 else "insufficient"

        return {
            "arabic_chars": ar_count,
            "latin_chars": lat_count,
            "total_chars": total,
            "arabic_ratio": ar_ratio,
            "latin_ratio": lat_ratio,
            "primary_script": primary
        }

    @staticmethod
    def inspect_page(page: fitz.Page) -> Dict[str, Any]:
        """
        Multi-factor analysis of a single PDF page:
        1. Text layer presence and Arabic unicode density
        2. Image area raster coverage
        3. Lexical density and script classification
        """
        page_rect = page.rect
        page_area = max(page_rect.width * page_rect.height, 1.0)

        # 1. Text layer extraction
        text = page.get_text().strip()
        script_info = PDFExtractor.analyze_text_script(text)

        # 2. Image coverage calculation
        image_list = page.get_images(full=True)
        total_image_area = 0.0
        for img in image_list:
            try:
                for bbox in page.get_image_rects(img[0]):
                    total_image_area += (bbox.width * bbox.height)
            except Exception:
                pass

        image_coverage = min(total_image_area / page_area, 1.0)

        # 3. Decision Logic
        # Case A: Strong selectable Arabic text layer
        if script_info["arabic_chars"] >= 35 and script_info["arabic_ratio"] >= 0.45:
            is_scanned = False
            page_type = "text"
        # Case B: Predominantly Latin / English text
        elif script_info["latin_chars"] >= 40 and script_info["latin_ratio"] >= 0.60:
            is_scanned = False
            page_type = "non_arabic_text"
        # Case C: Heavy image with low or garbage text
        elif image_coverage >= 0.40 or script_info["arabic_chars"] < 25:
            is_scanned = True
            page_type = "scanned"
        else:
            is_scanned = len(text) < 30
            page_type = "scanned" if is_scanned else "text"

        return {
            "page_type": page_type,
            "is_scanned": is_scanned,
            "image_coverage": round(image_coverage, 2),
            "script_info": script_info,
            "raw_text_length": len(text)
        }

    @staticmethod
    def inspect_pdf(filepath: str) -> Dict[str, Any]:
        """Inspects PDF to determine page count and overall scan vs native text distribution."""
        doc = fitz.open(filepath)
        total_pages = len(doc)
        text_pages_count = 0
        scanned_pages_count = 0
        non_arabic_count = 0

        sample_limit = min(total_pages, 15)
        for page_idx in range(sample_limit):
            page_meta = PDFExtractor.inspect_page(doc[page_idx])
            if page_meta["page_type"] == "non_arabic_text":
                non_arabic_count += 1
            elif page_meta["is_scanned"]:
                scanned_pages_count += 1
            else:
                text_pages_count += 1

        doc.close()

        is_predominantly_scanned = scanned_pages_count > text_pages_count
        is_non_arabic = non_arabic_count > (sample_limit * 0.6)

        return {
            "total_pages": total_pages,
            "is_scanned": is_predominantly_scanned,
            "is_non_arabic": is_non_arabic,
            "type_label": "Non-Arabic PDF (English/Latin)" if is_non_arabic else (
                "Scanned PDF (OCR Required)" if is_predominantly_scanned else "Native Text PDF"
            )
        }

    @staticmethod
    def extract_page_text(doc: fitz.Document, page_num: int) -> Tuple[str, bool, str]:
        """
        Extracts structured text from a specific 1-indexed page.
        Returns: (text: str, is_scanned: bool, page_type: str)
        """
        page = doc[page_num - 1]
        page_analysis = PDFExtractor.inspect_page(page)

        if page_analysis["is_scanned"]:
            return "", True, page_analysis["page_type"]

        # Preserve paragraph structure using text blocks
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], -b[0]))
        
        paragraphs = []
        for b in blocks:
            t = b[4].strip()
            if t:
                paragraphs.append(t)

        full_page_text = "\n\n".join(paragraphs).strip()
        return full_page_text, False, page_analysis["page_type"]
