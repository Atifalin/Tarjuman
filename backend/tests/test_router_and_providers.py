import os
import pytest
from backend.app.core.config import settings
from backend.app.providers.model_registry import ModelRegistry
from backend.app.providers.test_provider import MockTestProvider

def test_mock_provider_blocked_in_production(monkeypatch):
    # When APP_ENV is production, MockTestProvider instantiation MUST raise PermissionError
    monkeypatch.setattr(settings, "APP_ENV", "production")
    with pytest.raises(PermissionError):
        MockTestProvider()

def test_model_registry_capabilities():
    madlad = ModelRegistry.get_model("madlad400-7b-mt")
    assert madlad is not None
    assert madlad.translation_capable is True
    assert madlad.architecture == "seq2seq"
    assert ModelRegistry.is_arabic_to_urdu_verified("madlad400-7b-mt") is True

    qwen = ModelRegistry.get_model("qwen3:8b")
    assert qwen is not None
    assert qwen.review_capable is True

    gemini = ModelRegistry.get_model("gemini-3.6-flash")
    assert gemini is not None
    assert gemini.provider_name == "gemini"
