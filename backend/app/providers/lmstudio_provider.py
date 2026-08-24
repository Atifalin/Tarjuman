import time
import httpx
import logging
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.providers.base import (
    AIProvider,
    ChatModelAdapter,
    TranslationResult,
    ReviewResult,
    Tuple_Availability,
    ProviderClass,
    PrivacyClass
)

logger = logging.getLogger(__name__)

class LMStudioProvider(AIProvider, ChatModelAdapter):
    """
    LM Studio Local Provider (OpenAI-compatible local server).
    Communicates with local LM Studio instance at http://127.0.0.1:1234/v1.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.LMSTUDIO_BASE_URL).rstrip("/")

    def get_provider_name(self) -> str:
        return "lmstudio"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.LOCAL_AI

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    async def check_availability(self) -> Tuple_Availability:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/models")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    return Tuple_Availability(
                        is_available=True,
                        status_message=f"Connected to LM Studio ({len(models)} models loaded/available)",
                        details={"models": models, "url": self.base_url}
                    )
        except Exception as e:
            logger.debug(f"LM Studio connection check failed: {e}")

        return Tuple_Availability(
            is_available=False,
            status_message="LM Studio local server is not running or not reachable.",
            details={"url": self.base_url}
        )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, model: str = "local-model", **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(f"{self.base_url}/chat/completions", json=payload)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()

    async def translate_via_chat(self, source_text: str, model: str = "local-model", **kwargs) -> TranslationResult:
        t0 = time.perf_counter()
        system_prompt = (
            "You are a professional scholar translator specializing in Arabic to Urdu document translation.\n"
            "Translate the Arabic text accurately into standard scholarly Urdu.\n"
            "Output ONLY the Urdu translation. Do not include any explanations."
        )
        user_prompt = f"Arabic Text:\n{source_text}\n\nUrdu Translation:"
        output = await self.generate(user_prompt, system_prompt=system_prompt, model=model, **kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        return TranslationResult(
            source_text=source_text,
            translated_text=output,
            provider_name="lmstudio",
            model_name=model,
            latency_ms=latency,
            is_cloud=False
        )

    async def review_translation(
        self,
        source_arabic: str,
        candidate_urdu: str,
        glossary_terms: Optional[Dict[str, str]] = None,
        model: str = "local-model",
        **kwargs
    ) -> ReviewResult:
        t0 = time.perf_counter()
        prompt = (
            f"Review this Arabic to Urdu translation:\n"
            f"Original Arabic: {source_arabic}\n"
            f"Candidate Urdu: {candidate_urdu}\n"
            f"Output in format:\n"
            f"FINAL_URDU: <polished text>\n"
            f"VERDICT: <PASS | WARNING | REVIEW_REQUIRED>\n"
            f"NOTES: <notes>"
        )
        resp = await self.generate(prompt, model=model, **kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        final_urdu = candidate_urdu
        verdict = "PASS"
        notes = []
        for line in resp.split("\n"):
            line_s = line.strip()
            if line_s.startswith("FINAL_URDU:"):
                final_urdu = line_s.replace("FINAL_URDU:", "").strip()
            elif line_s.startswith("VERDICT:"):
                v = line_s.replace("VERDICT:", "").strip().upper()
                if v in ["PASS", "WARNING", "REVIEW_REQUIRED"]:
                    verdict = v
            elif line_s.startswith("NOTES:"):
                note = line_s.replace("NOTES:", "").strip()
                if note:
                    notes.append(note)

        return ReviewResult(
            source_text=source_arabic,
            candidate_urdu=candidate_urdu,
            revised_urdu=final_urdu,
            qa_verdict=verdict,
            comments=notes,
            provider_name="lmstudio",
            model_name=model,
            latency_ms=latency,
            is_cloud=False
        )

    async def test_arabic_urdu_model(self, model_id: str) -> Dict[str, Any]:
        test_source = "كيف حالك؟"
        try:
            result = await self.translate_via_chat(test_source, model=model_id)
            urdu = result.translated_text
            if not urdu or urdu == test_source:
                return {"success": False, "error": "Empty or echo response from LM Studio."}
            return {
                "success": True,
                "model": model_id,
                "source": test_source,
                "output": urdu,
                "latency_ms": result.latency_ms,
                "verified": True
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
