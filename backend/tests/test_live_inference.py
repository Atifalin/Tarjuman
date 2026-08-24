import os
import pytest
from backend.app.core.security import CredentialManager
from backend.app.providers.gemini_provider import GeminiProvider
from backend.app.providers.ollama_provider import OllamaProvider
from backend.app.providers.transformers_provider import TransformersProvider

@pytest.mark.asyncio
async def test_live_gemini_integration():
    """
    Integration test: Runs actual live Arabic -> Urdu translation if Gemini API key is configured.
    Explicitly skipped if no key is configured in Keychain or environment.
    """
    key = CredentialManager.get_gemini_api_key()
    if not key:
        pytest.skip("Gemini API Key is not configured. Skipping live cloud integration test.")

    prov = GeminiProvider()
    stat = await prov.check_availability()
    if not stat.is_available:
        pytest.skip(f"Gemini API check failed: {stat.status_message}")

    test_arabic = "كيف حالك؟"
    res = await prov.translate_direct(test_arabic, model="gemini-3.6-flash")
    
    assert res.translated_text != ""
    assert res.translated_text != test_arabic
    assert res.latency_ms > 0
    assert res.is_cloud is True

@pytest.mark.asyncio
async def test_live_ollama_integration():
    """
    Integration test: Runs actual live local translation if Ollama daemon is running with a model.
    Explicitly skipped if Ollama is offline.
    """
    prov = OllamaProvider()
    stat = await prov.check_availability()
    if not stat.is_available:
        pytest.skip("Local Ollama daemon is not running. Skipping live local test.")

    models = await prov.list_installed_models()
    if not models:
        pytest.skip("Ollama is running but no local models are installed.")

    model_to_test = models[0]
    res = await prov.translate_via_chat("السلام عليكم", model=model_to_test)
    assert res.translated_text != ""
    assert res.latency_ms > 0
