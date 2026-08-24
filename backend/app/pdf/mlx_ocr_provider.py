import base64
import logging
from typing import Tuple, Dict, Any
import fitz
import httpx
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class MLXOCRProvider:
    """
    Primary Arabic manuscript/book OCR engine: NAMAA-Space Qari-OCR-0.4.0-VL-4B-Instruct
    (fine-tuned Qwen3-VL-4B), served locally via mlx-vlm's OpenAI-compatible FastAPI server
    (`python -m mlx_vlm.server`). Runs natively on Apple Silicon via MLX/Metal — zero cloud
    transmission, no Ollama dependency.
    """

    OCR_SYSTEM_PROMPT = (
        "You are a specialized, scholarly Arabic manuscript and book transcription engine. "
        "Extract and transcribe all printed or handwritten Arabic text on this page with 100% accuracy. "
        "Preserve exact wording, headings, paragraph breaks, poetry formatting, numbers, and diacritics. "
        "Do not summarize, do not translate, and do not add explanatory commentary. Return ONLY the Arabic text."
    )

    @classmethod
    async def check_availability(cls) -> Dict[str, Any]:
        """Checks if the local MLX-VLM server is running and reachable."""
        url = settings.MLX_VLM_BASE_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{url}/models")
                if res.status_code == 200:
                    models = [m.get("id", "") for m in res.json().get("data", [])]
                    return {
                        "is_available": True,
                        "models": models,
                        "provider": "mlx_vlm",
                        "status_message": f"MLX-VLM server is ready ({', '.join(models) if models else 'model loads on first request'})."
                    }
        except Exception:
            pass

        return {
            "is_available": False,
            "models": [],
            "provider": "mlx_vlm",
            "status_message": "MLX-VLM server is not running (Setup Wizard \u2192 Install Qari-OCR MLX \u2192 Start Server)."
        }

    @classmethod
    async def ocr_page(
        cls,
        doc: fitz.Document,
        page_num: int,
        dpi: int = 200
    ) -> Tuple[str, bool, str]:
        """
        Transcribes a scanned PDF page using the local Qari-OCR MLX server.
        Returns: (transcribed_text, success, engine_name)
        """
        url = settings.MLX_VLM_BASE_URL.rstrip("/")
        try:
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            b64_image = base64.b64encode(img_bytes).decode("utf-8")

            payload = {
                "model": settings.MLX_OCR_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": cls.OCR_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe this page."},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2048,
                "stream": False
            }

            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(f"{url}/chat/completions", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"].strip()
                    if len(text) > 10:
                        logger.info(f"Qari-OCR (MLX) transcribed {len(text)} chars for page {page_num}")
                        return text, True, "Qari-OCR-0.4.0 (MLX)"
                else:
                    logger.warning(f"MLX-VLM server returned {resp.status_code} for page {page_num}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"Qari-OCR (MLX) failed for page {page_num}: {e}")

        return "", False, "Qari-OCR-0.4.0 (MLX)"
