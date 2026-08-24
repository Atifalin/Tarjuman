import time
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.app.core.config import settings
from backend.app.core.security import CredentialManager
from backend.app.database.connection import get_db
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

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"

class GeminiProvider(AIProvider, ChatModelAdapter):
    """
    Real Google Gemini API Cloud Provider.
    Requires an API key configured via Keychain or environment variable.
    Tracks quotas, request counts, and estimated tokens.
    Always marked as CLOUD AI.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    def get_provider_name(self) -> str:
        return "gemini"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.CLOUD_AI

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.CLOUD_USER_ENABLED

    def is_cloud(self) -> bool:
        return True

    def get_api_key(self) -> Optional[str]:
        if self._api_key:
            return self._api_key
        return CredentialManager.get_gemini_api_key()

    def record_usage(self, in_tokens: int, out_tokens: int):
        """Records daily cloud quota and token usage in database."""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with get_db() as conn:
                conn.execute("""
                INSERT INTO usage_stats (stat_date, cloud_requests_count, cloud_estimated_input_tokens, cloud_estimated_output_tokens)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    cloud_requests_count = cloud_requests_count + 1,
                    cloud_estimated_input_tokens = cloud_estimated_input_tokens + excluded.cloud_estimated_input_tokens,
                    cloud_estimated_output_tokens = cloud_estimated_output_tokens + excluded.cloud_estimated_output_tokens;
                """, (today, in_tokens, out_tokens))
        except Exception as e:
            logger.debug(f"Failed to record usage stats: {e}")

    async def check_availability(self) -> Tuple_Availability:
        key = self.get_api_key()
        if not key:
            return Tuple_Availability(
                is_available=False,
                status_message="Gemini API Key is not configured.",
                details={"configured": False, "official_url": "https://ai.google.dev/"}
            )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. Try listing models
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                res = await client.get(url)
                if res.status_code == 200:
                    models = [m.get("name", "").replace("models/", "") for m in res.json().get("models", [])]
                    gemini_models = [m for m in models if "gemini" in m]
                    return Tuple_Availability(
                        is_available=True,
                        status_message=f"Connected to Gemini API ({len(gemini_models)} models online)",
                        details={"configured": True, "models": gemini_models}
                    )

                # 2. Fallback: Probe generateContent directly on gemini-3.6-flash
                probe_url = f"{GEMINI_API_ENDPOINT}/gemini-3.6-flash:generateContent?key={key}"
                probe_payload = {
                    "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                    "generationConfig": {"maxOutputTokens": 5}
                }
                probe_res = await client.post(probe_url, json=probe_payload)
                if probe_res.status_code == 200:
                    return Tuple_Availability(
                        is_available=True,
                        status_message="Connected to Gemini API (gemini-3.6-flash verified)",
                        details={"configured": True, "models": ["gemini-3.6-flash", "gemini-3.6-pro"]}
                    )
                else:
                    return Tuple_Availability(
                        is_available=False,
                        status_message=f"Gemini API returned error: {probe_res.status_code} ({probe_res.text[:120]})",
                        details={"configured": True}
                    )
        except Exception as e:
            return Tuple_Availability(
                is_available=False,
                status_message=f"Network error connecting to Gemini API: {str(e)}",
                details={"configured": True}
            )

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, model: str = "gemini-3.6-flash", **kwargs) -> str:
        key = self.get_api_key()
        if not key:
            raise ValueError("Gemini API key is not configured. Please set API key in Settings.")

        # Clean model ID if it contains 'models/' prefix
        clean_model = model.replace("models/", "").strip()
        url = f"{GEMINI_API_ENDPOINT}/{clean_model}:generateContent?key={key}"
        
        # 1. Acquire Guardrail Permission (checks RPD hard cap, respects sliding-window RPM & TPM)
        estimated_input_tokens = len(prompt.split()) * 2
        from backend.app.providers.gemini_guardrails import GeminiGuardrails, GeminiQuotaExceededError
        await GeminiGuardrails.acquire_permission(clean_model, estimated_tokens=estimated_input_tokens)

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instructions: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.1),
                "maxOutputTokens": kwargs.get("max_tokens", 2048)
            }
        }

        # 2. Execute call with 429 adaptive backoff guard
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise RuntimeError("Gemini API returned no candidates.")
                    
                    text = candidates[0]["content"]["parts"][0]["text"].strip()
                    
                    # Record usage tokens in guardrails & database
                    usage = data.get("usageMetadata", {})
                    in_tokens = usage.get("promptTokenCount", estimated_input_tokens)
                    out_tokens = usage.get("candidatesTokenCount", len(text.split()) * 2)
                    GeminiGuardrails.record_call(clean_model, in_tokens, out_tokens)
                    
                    return text

                err_text = res.text

                # HTTP 429 (Resource Exhausted / Rate Limit Hit)
                if res.status_code == 429:
                    tier_cfg = GeminiGuardrails.get_tier_config(clean_model)
                    daily_stat = GeminiGuardrails.get_daily_usage(tier_cfg.tier_name)
                    
                    # Check if actually daily exhaustion vs per-minute RPM burst
                    is_daily_exhausted = (
                        daily_stat["requests_count"] >= tier_cfg.rpd_cap or
                        ("per day" in err_text.lower() and "per minute" not in err_text.lower())
                    )

                    if is_daily_exhausted:
                        raise GeminiQuotaExceededError(
                            f"Google Cloud Free Tier Daily Quota Exceeded for {tier_cfg.tier_name} "
                            f"(Limit: {tier_cfg.rpd_cap} RPD per GCP project). "
                            f"Switch project mode to local models or wait until midnight UTC.",
                            model_id=clean_model,
                            tier=tier_cfg.tier_name,
                            current_rpd=daily_stat["requests_count"],
                            max_rpd=tier_cfg.rpd_cap
                        )
                    
                    # Transient RPM (Requests Per Minute) burst -> back off exponentially
                    backoff_delay = (2 ** (attempt + 1)) * 3.0 # 6s, 12s, 24s
                    logger.warning(
                        f"Gemini API 429 Per-Minute Rate Limit on {clean_model} ({tier_cfg.rpm_cap} RPM). "
                        f"Attempt {attempt + 1}/{max_retries}. Backing off for {backoff_delay:.1f}s..."
                    )
                    await asyncio.sleep(backoff_delay)
                    last_error = RuntimeError(
                        f"Google Gemini Per-Minute Rate Limit reached ({tier_cfg.rpm_cap} RPM limit on {tier_cfg.tier_name}). "
                        f"Please wait a few seconds before retrying, or switch to local models."
                    )
                    continue

                if res.status_code == 403 and "not allowed by policy" in err_text:
                    raise RuntimeError(
                        "Google Cloud Key Policy Restriction (403): Your API Key has restriction policies blocking "
                        "'generativelanguage.googleapis.com'. Please check Google AI Studio (https://aistudio.google.com/app/apikey) "
                        "or Google Cloud Console API Key restrictions."
                    )
                elif res.status_code == 404:
                    raise RuntimeError(
                        f"Gemini Model Not Found (404): The requested model '{clean_model}' is not available on your account. "
                        f"Please try using 'gemini-3.6-flash' or 'gemini-1.5-flash'. ({err_text[:120]})"
                    )
                
                raise RuntimeError(f"Gemini API Error ({res.status_code}): {err_text}")

        if last_error:
            raise last_error
        raise RuntimeError("Gemini API request failed after retry attempts.")

    async def translate_via_chat(self, source_text: str, model: str = "gemini-3.6-flash") -> TranslationResult:
        """Alias for ChatModelAdapter interface compliance."""
        return await self.translate_direct(source_text, model=model)

    async def translate_direct(self, source_text: str, model: str = "gemini-3.6-flash") -> TranslationResult:
        t0 = time.perf_counter()
        clean_model = model.replace("models/", "").strip()
        system_prompt = (
            "You are a master academic scholar specializing in Arabic to Urdu document translation.\n"
            "Translate the Arabic text with utmost fidelity, nuance, and elegance into Urdu.\n"
            "Rules:\n"
            "1. Output ONLY the raw Urdu translation. Do not include markdown codeblocks, explanations, English commentary, or introductory phrases.\n"
            "2. Preserve all numbers, chapter markers, and Islamic terminologies accurately."
        )
        user_prompt = f"Arabic Text to translate:\n{source_text}\n\nUrdu Translation:"
        output = await self.generate(user_prompt, system_prompt=system_prompt, model=clean_model, **kwargs)
        latency = int((time.perf_counter() - t0) * 1000)

        # Clean any accidental conversational prefix
        clean_output = output
        for prefix in ["ترجمہ:", "Urdu Translation:", "الترجمة:", "Here is the translation:"]:
            if clean_output.startswith(prefix):
                clean_output = clean_output[len(prefix):].strip()

        return TranslationResult(
            source_text=source_text,
            translated_text=clean_output,
            provider_name="gemini",
            model_name=clean_model,
            latency_ms=latency,
            is_cloud=True
        )

    async def review_translation(
        self,
        source_arabic: str,
        candidate_urdu: str,
        glossary_terms: Optional[Dict[str, str]] = None,
        model: str = "gemini-3.6-flash",
        **kwargs
    ) -> ReviewResult:
        t0 = time.perf_counter()
        clean_model = model.replace("models/", "").strip()
        glossary_clause = ""
        if glossary_terms:
            terms_str = "\n".join([f"- {k} => {v}" for k, v in glossary_terms.items()])
            glossary_clause = f"\nMandatory Terminology:\n{terms_str}\n"

        prompt = (
            f"You are a Senior Editor and QA Specialist for Arabic to Urdu document translations.\n\n"
            f"Original Arabic Source:\n{source_arabic}\n\n"
            f"Candidate Urdu Translation:\n{candidate_urdu}\n"
            f"{glossary_clause}\n"
            f"Tasks:\n"
            f"1. Check if the Urdu accurately captures the entire Arabic text without hallucinations or dropped sentences.\n"
            f"2. Ensure elegant Nastaliq phrasing and grammatical correctness.\n"
            f"3. Polish and produce the final revised Urdu text.\n\n"
            f"Strict Output Format:\n"
            f"FINAL_URDU: <polished final urdu>\n"
            f"VERDICT: <PASS | WARNING | REVIEW_REQUIRED>\n"
            f"NOTES: <concise bulleted notes if any issues found>"
        )

        resp = await self.generate(prompt, model=clean_model, **kwargs)
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
            provider_name="gemini",
            model_name=clean_model,
            latency_ms=latency,
            is_cloud=True
        )

    async def test_arabic_urdu_model(self, model_id: str = "gemini-3.6-flash") -> Dict[str, Any]:
        test_source = "كيف حالك؟"
        clean_model = model_id.replace("models/", "").strip()
        try:
            result = await self.translate_direct(test_source, model=clean_model)
            urdu = result.translated_text
            if not urdu or urdu == test_source:
                return {"success": False, "error": "Empty or echo response from Gemini API."}
            return {
                "success": True,
                "model": clean_model,
                "source": test_source,
                "output": urdu,
                "latency_ms": result.latency_ms,
                "verified": True,
                "is_cloud": True
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
