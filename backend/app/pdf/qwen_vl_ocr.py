import os
import io
import base64
import logging
import fitz
import httpx
from typing import Tuple, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.pdf.ocr import OCRProvider

logger = logging.getLogger(__name__)

class QwenVLOCRProvider:
    """
    Scanned Page OCR Orchestrator.
    Tries engines in order of Arabic-transcription quality:
    1. Qari-OCR-0.4.0 (native MLX, Apple Silicon GPU) -- best Arabic/manuscript accuracy.
    2. Qwen2-VL / Qwen2.5-VL via Ollama -- general-purpose vision OCR fallback.
    3. Apple Vision OCR -- always-available on-device fallback.
    """

    SUPPORTED_MODELS = [
        "qwen2-vl:7b",
        "qwen2.5-vl:7b",
        "qwen2-vl:2b",
        "qwen2.5-vl:3b",
        "qwen2-vl"
    ]

    OCR_SYSTEM_PROMPT = (
        "You are a specialized, scholarly Arabic manuscript and book transcription engine. "
        "Extract and transcribe all printed or handwritten Arabic text on this page with 100% accuracy. "
        "Preserve exact wording, headings, paragraph breaks, poetry formatting, numbers, and diacritics. "
        "Do not summarize, do not translate, and do not add explanatory commentary. Return ONLY the Arabic text."
    )

    @classmethod
    async def check_availability(cls) -> Dict[str, Any]:
        """Checks if local Ollama daemon is running with a Qwen2-VL model installed."""
        url = settings.OLLAMA_BASE_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name", "") for m in res.json().get("models", [])]
                    for target in cls.SUPPORTED_MODELS:
                        for installed in models:
                            if target in installed.lower():
                                return {
                                    "is_available": True,
                                    "model_name": installed,
                                    "provider": "ollama",
                                    "status_message": f"Qwen2-VL local OCR model is ready ({installed})."
                                }
                    return {
                        "is_available": False,
                        "model_name": None,
                        "provider": "ollama",
                        "status_message": "Ollama is running, but Qwen2-VL is not pulled (run `ollama pull qwen2-vl:7b`)."
                    }
        except Exception:
            pass

        return {
            "is_available": False,
            "model_name": None,
            "provider": "none",
            "status_message": "Ollama is not running. Falling back to Apple Vision OCR."
        }

    @classmethod
    async def ocr_page(
        cls,
        doc: fitz.Document,
        page_num: int,
        dpi: int = 200
    ) -> Tuple[str, bool, str, bool]:
        """
        Transcribes a scanned PDF page.
        Returns: (transcribed_text, success, engine_name, is_fallback)
        """
        # 1. Try Qari-OCR-0.4.0 via local MLX server first (best Arabic manuscript accuracy)
        from backend.app.pdf.mlx_ocr_provider import MLXOCRProvider
        mlx_avail = await MLXOCRProvider.check_availability()
        if mlx_avail["is_available"]:
            text, ok, engine_name = await MLXOCRProvider.ocr_page(doc, page_num, dpi=dpi)
            if ok and text:
                return text, True, engine_name, False
            logger.warning(f"Qari-OCR (MLX) returned no usable text for page {page_num}. Falling back to Ollama/Apple Vision.")

        avail = await cls.check_availability()
        
        # If Qwen2-VL is ready, execute secondary vision transcription
        if avail["is_available"] and avail["model_name"]:
            model_name = avail["model_name"]
            try:
                page = doc[page_num - 1]
                # Render page to high-res image
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")
                b64_image = base64.b64encode(img_bytes).decode("utf-8")

                url = settings.OLLAMA_BASE_URL.rstrip("/")
                payload = {
                    "model": model_name,
                    "prompt": cls.OCR_SYSTEM_PROMPT,
                    "images": [b64_image],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 2048,
                    },
                    "keep_alive": "2m" # auto-unload after 2 minutes of idle time
                }

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(f"{url}/api/generate", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("response", "").strip()
                        if len(text) > 10:
                            logger.info(f"Qwen2-VL OCR transcribed {len(text)} chars for page {page_num}")
                            return text, True, f"Qwen2-VL ({model_name})", False

            except Exception as e:
                logger.warning(f"Qwen2-VL OCR failed for page {page_num}: {e}. Falling back to Apple Vision.")

        # Fallback to Apple Vision OCR
        text, ok, engine_name = OCRProvider.ocr_pdf_page(doc, page_num)
        return text, ok, f"Apple Vision OCR (Fallback)", True
