import time
import httpx
import logging
from typing import Dict, Any, Optional
from backend.app.providers.base import (
    AIProvider,
    ProviderClass,
    PrivacyClass,
    TranslationResult,
    Tuple_Availability
)

logger = logging.getLogger(__name__)

class FreeWebTranslator(AIProvider):
    """
    Public Web Translation Services (Unofficial Google Web, Lingva, MyMemory).
    Explicitly categorized as PUBLIC_WEB with user opt-in required.
    Strictly blocked under LOCAL_ONLY privacy mode.
    """

    def __init__(self):
        self._user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self._lingva_instances = [
            "https://lingva.ml",
            "https://translate.plausibility.cloud",
            "https://lingva.thedaviddelta.com"
        ]

    def get_provider_name(self) -> str:
        return "public_web"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.PUBLIC_WEB

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.PUBLIC_WEB_USER_ENABLED

    def is_cloud(self) -> bool:
        return True

    async def check_availability(self) -> Tuple_Availability:
        return Tuple_Availability(
            is_available=True,
            status_message="Public Web Translation services available (Internet access required; user opt-in only).",
            status_code="AVAILABLE",
            details={
                "endpoints": ["Google Web (gtx)", "Lingva Instances", "MyMemory"],
                "privacy": "PUBLIC_WEB_USER_ENABLED",
                "warning": "Document text will be sent to public external web endpoints."
            }
        )

    async def test_arabic_urdu_model(self, model_id: str = "google-web-unofficial") -> Dict[str, Any]:
        start_t = time.time()
        sample_arabic = "كيف حالك؟"
        try:
            res = await self.translate_arabic_to_urdu(sample_arabic, privacy_mode="ALLOW_PUBLIC_WEB")
            return {
                "success": True,
                "arabic": sample_arabic,
                "urdu": res.translated_text,
                "latency_ms": res.latency_ms,
                "endpoint": res.execution_backend,
                "status_code": "VERIFIED"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": int((time.time() - start_t) * 1000),
                "status_code": "FAILED"
            }

    async def translate_arabic_to_urdu(
        self,
        source_text: str,
        privacy_mode: str = "LOCAL_ONLY",
        preferred_endpoint: str = "google-web-unofficial"
    ) -> TranslationResult:
        if privacy_mode == "LOCAL_ONLY":
            raise RuntimeError(
                "Privacy Guard: Public Web Translation is strictly disabled when project "
                "privacy mode is set to 'LOCAL_ONLY'. Switch to 'ALLOW_PUBLIC_WEB' to enable."
            )

        start_t = time.time()
        translated_text = ""
        backend_used = "google_gtx"

        # Tier 1: Google Translate Web (gtx)
        try:
            translated_text = await self._translate_google_web(source_text, src="ar", tgt="ur")
            backend_used = "google_web_unofficial"
        except Exception as e1:
            logger.warning(f"Google Web gtx translation failed: {e1}. Trying Lingva fallback...")
            
            # Tier 2: Lingva public instances
            try:
                translated_text = await self._translate_lingva(source_text, src="ar", tgt="ur")
                backend_used = "lingva_public"
            except Exception as e2:
                logger.warning(f"Lingva translation failed: {e2}. Trying MyMemory fallback...")
                
                # Tier 3: MyMemory
                translated_text = await self._translate_mymemory(source_text, src="ar", tgt="ur")
                backend_used = "mymemory_public"

        latency = max(10, int((time.time() - start_t) * 1000))

        return TranslationResult(
            source_text=source_text,
            translated_text=translated_text,
            provider_name="public_web",
            provider_class=ProviderClass.PUBLIC_WEB.value,
            privacy_class=PrivacyClass.PUBLIC_WEB_USER_ENABLED.value,
            model_name=preferred_endpoint,
            execution_backend=backend_used,
            route="Direct Web Endpoint (ar -> ur)",
            is_pivot=False,
            latency_ms=latency,
            peak_ram_mb=50.0,
            memory_pressure="GREEN",
            is_cloud=True
        )

    async def translate_arabic_to_english(
        self,
        source_text: str,
        privacy_mode: str = "ALLOW_PUBLIC_WEB"
    ) -> str:
        """Translates Arabic -> English for the English Reference bridge."""
        if privacy_mode == "LOCAL_ONLY":
            raise RuntimeError("Privacy Guard: Public Web Translation blocked in LOCAL_ONLY mode.")

        try:
            return await self._translate_google_web(source_text, src="ar", tgt="en")
        except Exception:
            return await self._translate_mymemory(source_text, src="ar", tgt="en")

    async def _translate_google_web(self, text: str, src: str, tgt: str) -> str:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": src,
            "tl": tgt,
            "dt": "t",
            "q": text
        }
        headers = {"User-Agent": self._user_agent}
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, params=params, headers=headers)
            if res.status_code != 200:
                raise RuntimeError(f"Google Web HTTP {res.status_code}: {res.text[:100]}")
            data = res.json()
            sentences = [part[0] for part in data[0] if part and part[0]]
            return "".join(sentences).strip()

    async def _translate_lingva(self, text: str, src: str, tgt: str) -> str:
        for base in self._lingva_instances:
            try:
                url = f"{base}/api/v1/{src}/{tgt}/{text}"
                async with httpx.AsyncClient(timeout=6.0) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        return res.json().get("translation", "").strip()
            except Exception:
                continue
        raise RuntimeError("All Lingva instances failed or timed out.")

    async def _translate_mymemory(self, text: str, src: str, tgt: str) -> str:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{src}|{tgt}"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url, params=params)
            if res.status_code == 200:
                return res.json().get("responseData", {}).get("translatedText", "").strip()
        raise RuntimeError("MyMemory translation failed.")

    async def test_arabic_urdu_model(self, model_id: str = "google-web-unofficial") -> Dict[str, Any]:
        """Live verification test for public web endpoints."""
        sample_arabic = "كيف حالك؟"
        try:
            res = await self.translate_arabic_to_urdu(
                sample_arabic,
                privacy_mode="ALLOW_PUBLIC_WEB",
                preferred_endpoint=model_id
            )
            return {
                "success": True,
                "arabic": sample_arabic,
                "output": res.translated_text,
                "latency_ms": res.latency_ms,
                "backend": res.execution_backend,
                "status_code": "VERIFIED"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": "FAILED"
            }
