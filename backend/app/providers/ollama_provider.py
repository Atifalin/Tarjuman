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

class OllamaProvider(AIProvider, ChatModelAdapter):
    """
    Ollama Local AI Provider.
    Interacts directly with local Ollama daemon at http://127.0.0.1:11434.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    def get_provider_name(self) -> str:
        return "ollama"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.LOCAL_AI

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    async def check_availability(self) -> Tuple_Availability:
        """Checks if local Ollama daemon is reachable and lists installed models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    return Tuple_Availability(
                        is_available=True,
                        status_message=f"Connected to Ollama ({len(models)} local models found)",
                        details={"models": models, "url": self.base_url}
                    )
        except Exception as e:
            logger.debug(f"Ollama check failed: {e}")
            
        return Tuple_Availability(
            is_available=False,
            status_message="Ollama is not running or not installed.",
            details={"url": self.base_url}
        )

    async def list_installed_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, model: str = "qwen3:8b", **kwargs) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.1),
                "num_predict": kwargs.get("max_tokens", 1024)
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            res.raise_for_status()
            return res.json().get("response", "").strip()

    async def translate_via_chat(self, source_text: str, model: str = "qwen3:8b", **kwargs) -> TranslationResult:
        t0 = time.perf_counter()
        system_prompt = (
            "You are a professional scholarly translator specializing in Arabic to Urdu document translation.\n"
            "Translate the given Arabic text accurately into elegant, fluent Urdu in Nastaliq-style scholarly phrasing.\n"
            "Rules:\n"
            "1. Output ONLY the Urdu translation. Do not include any explanations, English commentary, or introductory phrases.\n"
            "2. Preserve all numbers, dates, and Quranic/Hadith references with utmost precision."
        )
        user_prompt = f"Arabic Text:\n{source_text}\n\nUrdu Translation:"
        output = await self.generate(user_prompt, system_prompt=system_prompt, model=model, **kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        return TranslationResult(
            source_text=source_text,
            translated_text=output,
            provider_name="ollama",
            model_name=model,
            latency_ms=latency,
            is_cloud=False
        )

    async def review_translation(
        self,
        source_arabic: str,
        candidate_urdu: str,
        glossary_terms: Optional[Dict[str, str]] = None,
        model: str = "qwen3:8b",
        **kwargs
    ) -> ReviewResult:
        t0 = time.perf_counter()
        glossary_clause = ""
        if glossary_terms:
            terms_str = "\n".join([f"- Arabic: {k} -> Preferred Urdu: {v}" for k, v in glossary_terms.items()])
            glossary_clause = f"\nRequired Glossary Terminology:\n{terms_str}\n"

        prompt = (
            f"You are a senior reviewer for Arabic to Urdu translations.\n"
            f"Original Arabic:\n{source_arabic}\n\n"
            f"Candidate Urdu Translation:\n{candidate_urdu}\n"
            f"{glossary_clause}\n"
            f"Tasks:\n"
            f"1. Check if the Urdu accurately reflects the Arabic meaning without omissions.\n"
            f"2. Ensure scholarly Urdu fluency.\n"
            f"3. Output the polished Final Urdu Translation.\n"
            f"Output format:\n"
            f"FINAL_URDU: <the final polished urdu text>\n"
            f"VERDICT: <PASS | WARNING | REVIEW_REQUIRED>\n"
            f"NOTES: <brief explanation if issues found>"
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
            provider_name="ollama",
            model_name=model,
            latency_ms=latency,
            is_cloud=False
        )

    async def test_arabic_urdu_model(self, model_id: str) -> Dict[str, Any]:
        """Performs a live Arabic -> Urdu translation verification test."""
        test_source = "كيف حالك؟"
        try:
            result = await self.translate_via_chat(test_source, model=model_id)
            urdu = result.translated_text
            
            # Verify real non-empty result
            if not urdu or urdu == test_source:
                return {"success": False, "error": "Model returned empty or identical text."}
            
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
