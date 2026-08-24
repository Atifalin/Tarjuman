import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import init_db
from backend.app.providers.gemini_guardrails import (
    GeminiGuardrails,
    GeminiQuotaExceededError,
    TIER_PROFILES
)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_tier_resolution_and_caps():
    # 1. Flash-Lite Tier
    assert GeminiGuardrails.get_model_tier("gemini-2.5-flash-lite") == "flash-lite"
    assert GeminiGuardrails.get_model_tier("gemini-2.0-flash-lite") == "flash-lite"
    cfg_lite = GeminiGuardrails.get_tier_config("gemini-2.5-flash-lite")
    assert cfg_lite.rpm_cap == 15
    assert cfg_lite.tpm_cap == 250_000
    assert cfg_lite.rpd_cap == 1000

    # 2. Flash Tier
    assert GeminiGuardrails.get_model_tier("gemini-3.6-flash") == "flash"
    assert GeminiGuardrails.get_model_tier("gemini-2.5-flash") == "flash"
    assert GeminiGuardrails.get_model_tier("gemini-1.5-flash") == "flash"
    cfg_flash = GeminiGuardrails.get_tier_config("gemini-3.6-flash")
    assert cfg_flash.rpm_cap == 10
    assert cfg_flash.tpm_cap == 250_000
    assert cfg_flash.rpd_cap == 250

    # 3. Pro Tier
    assert GeminiGuardrails.get_model_tier("gemini-3.6-pro") == "pro"
    assert GeminiGuardrails.get_model_tier("gemini-1.5-pro") == "pro"
    cfg_pro = GeminiGuardrails.get_tier_config("gemini-3.6-pro")
    assert cfg_pro.rpm_cap == 2
    assert cfg_pro.tpm_cap == 32_000
    assert cfg_pro.rpd_cap == 50

def test_record_call_and_daily_usage():
    # Record a test call on Flash
    GeminiGuardrails.record_call("gemini-3.6-flash", in_tokens=500, out_tokens=300)
    usage = GeminiGuardrails.get_daily_usage("flash")
    assert usage["requests_count"] >= 1
    assert usage["input_tokens"] >= 500
    assert usage["output_tokens"] >= 300

@pytest.mark.asyncio
async def test_daily_rpd_hard_stop_enforcement():
    # Mock tier config with small cap to test hard stop
    original_cap = TIER_PROFILES["pro"].rpd_cap
    TIER_PROFILES["pro"].rpd_cap = 1
    try:
        GeminiGuardrails.record_call("gemini-3.6-pro", in_tokens=100, out_tokens=100)
        # Second call should be proactively rejected by guardrails
        with pytest.raises(GeminiQuotaExceededError) as exc_info:
            await GeminiGuardrails.acquire_permission("gemini-3.6-pro")
        
        assert "Google Cloud Free Tier Daily Quota Exceeded" in str(exc_info.value)
        assert exc_info.value.max_rpd == 1
    finally:
        TIER_PROFILES["pro"].rpd_cap = original_cap

def test_gemini_quota_api_endpoint():
    res = client.get("/api/providers/gemini-quota")
    assert res.status_code == 200
    data = res.json()
    assert "date" in data
    assert "tiers" in data
    assert "flash" in data["tiers"]
    flash_tier = data["tiers"]["flash"]
    assert flash_tier["rpm_cap"] == 10
    assert flash_tier["rpd_cap"] == 250
    assert flash_tier["tpm_cap"] == 250_000
