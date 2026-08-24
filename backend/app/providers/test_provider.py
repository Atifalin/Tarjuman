import os
import time
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings
from backend.app.providers.base import (
    AIProvider,
    ChatModelAdapter,
    TranslationModelAdapter,
    TranslationResult,
    ReviewResult,
    Tuple_Availability,
    ProviderClass,
    PrivacyClass
)

class MockTestProvider(AIProvider, TranslationModelAdapter, ChatModelAdapter):
    """
    STRICTLY FOR AUTOMATED BACKEND UNIT TESTS.
    Never visible or selectable in normal production workflows.
    Throws an error if accessed when APP_ENV != 'test'.
    """

    def __init__(self):
        if settings.APP_ENV != "test":
            raise PermissionError(
                "MockTestProvider is strictly restricted to test environments (APP_ENV=test). "
                "Production workflows must use real AI providers."
            )

    def get_provider_name(self) -> str:
        return "TEST ONLY — FAKE PROVIDER"

    def get_provider_class(self) -> ProviderClass:
        return ProviderClass.TEST

    def get_privacy_class(self) -> PrivacyClass:
        return PrivacyClass.OFFLINE

    def is_cloud(self) -> bool:
        return False

    async def check_availability(self) -> Tuple_Availability:
        return Tuple_Availability(
            is_available=True,
            status_message="Test Mock Engine (FOR UNIT TESTING ONLY)",
            details={"is_mock": True}
        )

    async def translate(self, source_text: str, **kwargs) -> TranslationResult:
        return TranslationResult(
            source_text=source_text,
            translated_text="[ٹیسٹ ترجمہ]: یہ ایک خودکار یونٹ ٹیسٹ کا فرضی آؤٹ پٹ ہے۔",
            provider_name="TEST ONLY — FAKE PROVIDER",
            model_name="mock-test-model",
            latency_ms=10,
            peak_ram_mb=50.0,
            memory_pressure="GREEN",
            is_cloud=False
        )

    async def translate_via_chat(self, source_text: str, model: str) -> TranslationResult:
        return await self.translate(source_text)

    async def generate(self, prompt: str, **kwargs) -> str:
        return "[Test Mock Generated Output]"

    async def review_translation(
        self,
        source_arabic: str,
        candidate_urdu: str,
        glossary_terms: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None
    ) -> ReviewResult:
        return ReviewResult(
            source_text=source_arabic,
            candidate_urdu=candidate_urdu,
            revised_urdu=candidate_urdu,
            qa_verdict="PASS",
            comments=["[TEST HARNESS]: Automatic QA passed"],
            provider_name="TEST ONLY — FAKE PROVIDER",
            model_name="mock-test-model",
            latency_ms=10,
            is_cloud=False
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        return "[TEST ONLY OUTPUT]"

    async def test_arabic_urdu_model(self, model_id: str) -> Dict[str, Any]:
        return {
            "success": True,
            "model": "mock-test-model",
            "source": "كيف حالك؟",
            "output": "آپ کیسے ہیں؟",
            "latency_ms": 5,
            "verified": True,
            "is_test_mock": True
        }
