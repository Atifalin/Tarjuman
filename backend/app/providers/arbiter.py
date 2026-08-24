import logging
from typing import Dict, Any
from backend.app.hardware.monitor import HardwareMonitor
from backend.app.pdf.qwen_vl_ocr import QwenVLOCRProvider
from backend.app.pdf.ocr import OCRProvider
from backend.app.providers.nllb_provider import NLLBProvider
from backend.app.providers.argos_provider import ArgosProvider

logger = logging.getLogger(__name__)

class ResourceArbiter:
    """
    100% Local-First Resource Arbiter for Tarjuman.
    Evaluates hardware memory pressure and local model availability to select
    optimal OCR and Translation engines per job with full transparency.
    Zero Cloud APIs, Zero Network Transmissions.
    """

    @classmethod
    async def decide_engines(cls) -> Dict[str, Any]:
        """
        Determines the active OCR and Translation engines based on installed models and hardware telemetry.
        """
        hw = HardwareMonitor.get_hardware_status()
        mem_pressure = hw.get("memory_pressure", "GREEN")
        ram_percent = hw.get("ram_percent", 50.0)

        # 1. Evaluate OCR Engine Chain: Qwen2-VL -> Apple Vision OCR
        qwen_avail = await QwenVLOCRProvider.check_availability()
        
        # If Qwen2-VL is available and RAM is not critical (<85%), use Qwen2-VL
        if qwen_avail.get("is_available") and ram_percent < 85.0 and mem_pressure != "RED":
            ocr_engine = "qwen2_vl"
            ocr_is_fallback = False
            ocr_label = f"Qwen2-VL ({qwen_avail.get('model_name', '7B')})"
            ocr_reason = "Primary Vision-Language OCR"
        else:
            ocr_engine = "apple_vision"
            ocr_is_fallback = True
            ocr_label = "Apple Vision OCR (Fallback)"
            if qwen_avail.get("is_available"):
                ocr_reason = f"Fallback triggered (High Memory: {ram_percent}%)"
            else:
                ocr_reason = "Fallback triggered (Qwen2-VL not pulled in Ollama)"

        # 2. Evaluate Translation Engine Chain: NLLB-200 -> Argos Translate
        nllb_prov = NLLBProvider()
        argos_prov = ArgosProvider()

        nllb_avail = await nllb_prov.check_availability()
        argos_avail = await argos_prov.check_availability()

        if nllb_avail.is_available:
            trans_engine = "nllb-200-3.3b"
            trans_is_fallback = False
            trans_label = "Meta NLLB-200 (Direct ar → ur)"
            trans_route = "ar -> ur (Direct)"
            trans_ready = True
        elif argos_avail.is_available:
            trans_engine = "argos-translate"
            trans_is_fallback = True
            trans_label = "Argos Translate (Fallback ar → en → ur)"
            trans_route = "ar -> en -> ur"
            trans_ready = True
        else:
            trans_engine = "none"
            trans_is_fallback = False
            trans_label = "No Local Engine Ready"
            trans_route = "none"
            trans_ready = False

        status = "READY" if trans_ready else "INSTALL_REQUIRED"
        status_message = (
            f"Ready: OCR via {ocr_label} | Translation via {trans_label}"
            if trans_ready
            else "No local Urdu translation engine installed. Click to install NLLB or Argos."
        )

        return {
            "status": status,
            "status_message": status_message,
            "ocr": {
                "engine": ocr_engine,
                "is_fallback": ocr_is_fallback,
                "label": ocr_label,
                "reason": ocr_reason
            },
            "translation": {
                "engine": trans_engine,
                "is_fallback": trans_is_fallback,
                "label": trans_label,
                "route": trans_route,
                "ready": trans_ready
            },
            "hardware": {
                "ram_percent": ram_percent,
                "memory_pressure": mem_pressure,
                "process_memory_mb": hw.get("process_memory_mb", 0.0)
            }
        }
