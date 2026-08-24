from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.app.core.security import CredentialManager
from backend.app.providers.model_registry import ModelRegistry
from backend.app.providers.ollama_provider import OllamaProvider
from backend.app.providers.lmstudio_provider import LMStudioProvider
from backend.app.providers.gemini_provider import GeminiProvider
from backend.app.providers.transformers_provider import TransformersProvider
from backend.app.database.connection import get_db

router = APIRouter(prefix="/api/providers", tags=["Providers"])

class GeminiKeyRequest(BaseModel):
    api_key: str

class TestModelRequest(BaseModel):
    provider_name: str
    model_id: str

from backend.app.providers.argos_provider import ArgosProvider
from backend.app.providers.apple_provider import AppleTranslationProvider
from backend.app.providers.free_web_provider import FreeWebTranslator

@router.get("/status")
async def get_providers_status():
    """Checks real connectivity status of all 5 provider categories."""
    ollama = OllamaProvider()
    lmstudio = LMStudioProvider()
    gemini = GeminiProvider()
    transformers = TransformersProvider()
    argos = ArgosProvider()
    apple = AppleTranslationProvider()
    public_web = FreeWebTranslator()

    ollama_stat = await ollama.check_availability()
    lmstudio_stat = await lmstudio.check_availability()
    gemini_stat = await gemini.check_availability()
    transformers_stat = await transformers.check_availability()
    argos_stat = await argos.check_availability()
    apple_stat = await apple.check_availability()
    web_stat = await public_web.check_availability()

    # Get cloud daily quota stats
    cloud_stats = {"today_requests": 0, "today_input_tokens": 0, "today_output_tokens": 0}
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM usage_stats WHERE stat_date = ?;", (today,))
            row = cursor.fetchone()
            if row:
                cloud_stats["today_requests"] = row["cloud_requests_count"]
                cloud_stats["today_input_tokens"] = row["cloud_estimated_input_tokens"]
                cloud_stats["today_output_tokens"] = row["cloud_estimated_output_tokens"]
    except Exception:
        pass

    # Overall system readiness: at least one real provider must be ready
    is_any_ready = (
        ollama_stat.is_available or
        lmstudio_stat.is_available or
        gemini_stat.is_available or
        transformers_stat.is_available or
        argos_stat.is_available or
        apple_stat.is_available or
        web_stat.is_available
    )

    return {
        "system_ready": is_any_ready,
        "status_label": "READY" if is_any_ready else "SETUP REQUIRED",
        "providers": {
            "ollama": ollama_stat.model_dump(),
            "lmstudio": lmstudio_stat.model_dump(),
            "gemini": gemini_stat.model_dump(),
            "transformers": transformers_stat.model_dump(),
            "argos": argos_stat.model_dump(),
            "apple_translation": apple_stat.model_dump(),
            "public_web": web_stat.model_dump()
        },
        "cloud_usage": cloud_stats
    }

@router.get("/gemini-quota")
def get_gemini_quota_status():
    """
    Returns live structured Free Tier quota telemetry (RPM, TPM, and RPD caps per model tier).
    Strictly enforced per GCP project:
    - Flash-Lite: 15 RPM / 250k TPM / 1000 RPD
    - Flash: 10 RPM / 250k TPM / 250 RPD
    - Pro: 2 RPM / 32k TPM / 50 RPD
    """
    from backend.app.providers.gemini_guardrails import GeminiGuardrails
    return GeminiGuardrails.get_all_quotas_summary()

@router.get("/models")
def get_model_registry():
    """Lists all verified model capabilities and roles."""
    return ModelRegistry.list_all_models()

@router.post("/gemini/configure-key")
def configure_gemini_key(req: GeminiKeyRequest):
    """Saves Gemini API key securely in macOS Keychain / local secret storage."""
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
    success = CredentialManager.set_gemini_api_key(req.api_key.strip())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store API key in Keychain.")
    return {"success": True, "message": "Gemini API Key saved securely."}

@router.delete("/gemini/delete-key")
def delete_gemini_key():
    CredentialManager.delete_gemini_api_key()
    return {"success": True, "message": "Gemini API key deleted."}

@router.post("/test-model")
async def test_arabic_model(req: TestModelRequest):
    """
    Executes a real Arabic -> Urdu test translation to verify engine capability.
    Validates:
    - non-empty response
    - source != target
    - Arabic/Urdu script present
    - no model refusal
    - no system/network error
    """
    import re
    pname = req.provider_name.lower()
    
    if pname == "gemini":
        prov = GeminiProvider()
    elif pname == "lmstudio":
        prov = LMStudioProvider()
    elif pname == "transformers":
        prov = TransformersProvider()
    elif pname in ["argos", "argos-translate"]:
        prov = ArgosProvider()
    elif pname in ["apple", "apple_translation", "apple-native-translation"]:
        prov = AppleTranslationProvider()
    elif pname in ["web", "public_web", "google_web", "google-web-unofficial", "lingva", "mymemory"]:
        prov = FreeWebTranslator()
    elif pname == "mlx":
        from backend.app.providers.mlx_provider import MLXProvider
        prov = MLXProvider()
    else:
        prov = OllamaProvider()

    res = await prov.test_arabic_urdu_model(req.model_id)
    if not res.get("success"):
        return res

    output_text = res.get("output", "").strip()
    source_text = res.get("source", "كيف حالك؟").strip()

    # Strict Criteria:
    # 1. Non-empty
    if not output_text:
        return {"success": False, "error": "Model returned empty response."}

    # 2. Not echo
    if output_text == source_text:
        return {"success": False, "error": "Model echoed the Arabic source without translating."}

    # 3. Script block check (Allow Latin script for English reference bridge models)
    is_english_ref = req.model_id in ["apple-native-translation"] or pname in ["apple", "apple_translation"]
    if not is_english_ref:
        has_script = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F]", output_text))
        if not has_script:
            return {"success": False, "error": "Model output does not contain expected Arabic/Urdu script."}

    # 4. Refusal check
    refusal_keywords = ["cannot translate", "as an ai", "i am sorry", "content policy", "معذرت"]
    if any(rf in output_text.lower() for rf in refusal_keywords):
        return {"success": False, "error": "Model generated a disclaimer or refusal instead of translating."}

    return {
        "success": True,
        "model": req.model_id,
        "provider": pname,
        "source": source_text,
        "output": output_text,
        "latency_ms": res.get("latency_ms", 0),
        "status_label": "MODEL VERIFIED",
        "verified": True
    }
