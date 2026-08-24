import os
import sys
import tempfile
import subprocess
import logging
from typing import Tuple, Optional
from PIL import Image
import fitz

logger = logging.getLogger(__name__)

MAC_VISION_OCR_BIN = os.path.join(os.path.dirname(__file__), "mac_vision_ocr")

class OCRProvider:
    """
    High-Fidelity Arabic OCR Engine for Scanned PDFs.
    
    Tiers:
    1. Native Apple Vision Framework (Built into macOS on Apple Silicon, 0 external dependencies, high accuracy on Arabic).
    2. Tesseract OCR (with `ara` language model if installed).
    3. Google Gemini Multimodal Cloud OCR (if API key is configured).
    """

    @classmethod
    def _ensure_mac_vision_binary(cls) -> Optional[str]:
        """Ensures the native Apple Vision OCR CLI binary is compiled on macOS."""
        if sys.platform != "darwin":
            return None
        
        if os.path.exists(MAC_VISION_OCR_BIN) and os.access(MAC_VISION_OCR_BIN, os.X_OK):
            return MAC_VISION_OCR_BIN

        # Attempt on-the-fly compilation using system clang
        src_path = os.path.join(os.path.dirname(__file__), "mac_vision_ocr.m")
        if os.path.exists(src_path):
            try:
                cmd = [
                    "clang",
                    "-framework", "Foundation",
                    "-framework", "Vision",
                    "-framework", "AppKit",
                    "-framework", "CoreGraphics",
                    "-O3",
                    src_path,
                    "-o", MAC_VISION_OCR_BIN
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0 and os.path.exists(MAC_VISION_OCR_BIN):
                    os.chmod(MAC_VISION_OCR_BIN, 0o755)
                    logger.info("Compiled native Apple Vision OCR binary successfully.")
                    return MAC_VISION_OCR_BIN
            except Exception as e:
                logger.debug(f"Failed compiling mac_vision_ocr: {e}")

        return None

    @classmethod
    def is_ocr_available(cls) -> bool:
        if sys.platform == "darwin" and cls._ensure_mac_vision_binary():
            return True
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            pass
        return False

    @classmethod
    def ocr_pdf_page(cls, doc: fitz.Document, page_num: int) -> Tuple[str, bool, str]:
        """
        Renders PDF page to image pixmap and performs Arabic OCR.
        Returns: (extracted_text: str, success: bool, message: str)
        """
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=200)

        # 1. Try Native Apple Silicon Vision Framework on macOS
        vision_bin = cls._ensure_mac_vision_binary()
        if vision_bin:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                tmp_path = tmp_img.name

            try:
                pix.save(tmp_path)
                res = subprocess.run(
                    [vision_bin, tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if res.returncode == 0 and res.stdout.strip():
                    text = res.stdout.strip()
                    return text, True, "Apple Vision OCR completed."
            except Exception as e:
                logger.warning(f"Apple Vision OCR failed on page {page_num}: {e}")
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        # 2. Try PyTesseract if available
        try:
            import pytesseract
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img, lang="ara")
            clean_text = text.strip()
            if clean_text:
                return clean_text, True, "Tesseract OCR completed."
        except Exception as e:
            logger.debug(f"Tesseract OCR not available: {e}")

        return "", False, "No OCR engine available to transcribe scanned Arabic page."
