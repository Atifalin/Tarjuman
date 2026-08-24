import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel
from backend.app.database.connection import get_db

logger = logging.getLogger(__name__)

class ModelTierConfig(BaseModel):
    tier_name: str
    rpm_cap: int           # Requests per Minute
    tpm_cap: int           # Tokens per Minute
    rpd_cap: int           # Requests per Day (Free tier per GCP project)
    min_spacing_seconds: float # Minimum spacing between calls = 60.0 / rpm_cap

# Strict Google Cloud Free Tier Specifications (per GCP Project)
TIER_PROFILES: Dict[str, ModelTierConfig] = {
    "flash-lite": ModelTierConfig(
        tier_name="Gemini Flash-Lite",
        rpm_cap=15,
        tpm_cap=250_000,
        rpd_cap=1000,
        min_spacing_seconds=4.0  # 60 / 15 = 4.0s
    ),
    "flash": ModelTierConfig(
        tier_name="Gemini Flash",
        rpm_cap=10,
        tpm_cap=250_000,
        rpd_cap=250,
        min_spacing_seconds=6.0  # 60 / 10 = 6.0s
    ),
    "pro": ModelTierConfig(
        tier_name="Gemini Pro",
        rpm_cap=2,
        tpm_cap=32_000,
        rpd_cap=50,
        min_spacing_seconds=30.0 # 60 / 2 = 30.0s
    )
}

class GeminiQuotaExceededError(Exception):
    """Raised when free tier daily requests or project quota caps are reached."""
    def __init__(self, message: str, model_id: str, tier: str, current_rpd: int, max_rpd: int):
        super().__init__(message)
        self.model_id = model_id
        self.tier = tier
        self.current_rpd = current_rpd
        self.max_rpd = max_rpd

class GeminiGuardrails:
    """
    Strict Rate Limiting & Quota Protection for Google Gemini Free Tier.
    
    Protects against HTTP 429 errors and quota exhaustion across long-running document batches:
    1. Model-Structured Tier Resolution (Flash-Lite: 15 RPM / 250k TPM / 1000 RPD; Flash: 10 RPM / 250k TPM / 250 RPD; Pro: 2 RPM / 32k TPM / 50 RPD)
    2. Proactive Sliding-Window Pacing (asynchronously paces in-flight requests to respect RPM/TPM)
    3. Strict Daily RPD Guard (hard stops before exceeding 250/1000 RPD per GCP project)
    4. Adaptive Exponential Backoff with Jitter for transient HTTP 429
    """

    # In-memory sliding window history: tier -> list of (timestamp, token_count)
    _sliding_windows: Dict[str, List[Tuple[float, int]]] = {
        "flash-lite": [],
        "flash": [],
        "pro": []
    }
    _lock = asyncio.Lock()

    @classmethod
    def get_model_tier(cls, model_id: str) -> str:
        """Resolves model string to tier profile: 'flash-lite', 'flash', or 'pro'."""
        m = model_id.lower().replace("models/", "").strip()
        if "lite" in m or "flash-lite" in m:
            return "flash-lite"
        elif "pro" in m:
            return "pro"
        else:
            # Default to standard Flash tier (gemini-3.6-flash, gemini-2.5-flash, gemini-1.5-flash, etc.)
            return "flash"

    @classmethod
    def get_tier_config(cls, model_id: str) -> ModelTierConfig:
        tier = cls.get_model_tier(model_id)
        return TIER_PROFILES.get(tier, TIER_PROFILES["flash"])

    @classmethod
    def get_daily_usage(cls, tier: str, date_str: Optional[str] = None) -> Dict[str, int]:
        """Queries SQLite for total requests and tokens used today for a specific tier."""
        target_date = date_str or datetime.now().strftime("%Y-%m-%d")
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT COUNT(*) as req_count,
                       COALESCE(SUM(input_tokens), 0) as total_in,
                       COALESCE(SUM(output_tokens), 0) as total_out
                FROM gemini_usage_log
                WHERE stat_date = ? AND model_tier = ?;
                """, (target_date, tier))
                row = cursor.fetchone()
                if row:
                    return {
                        "requests_count": row["req_count"],
                        "input_tokens": row["total_in"],
                        "output_tokens": row["total_out"]
                    }
        except Exception as e:
            logger.debug(f"Error querying daily gemini usage: {e}")

        return {"requests_count": 0, "input_tokens": 0, "output_tokens": 0}

    @classmethod
    def record_call(cls, model_id: str, in_tokens: int, out_tokens: int):
        """Records completed call in database and memory window."""
        tier = cls.get_model_tier(model_id)
        now_ts = time.time()
        now_date = datetime.now().strftime("%Y-%m-%d")
        now_iso = datetime.now().isoformat()

        # Update sliding window
        cls._sliding_windows.setdefault(tier, []).append((now_ts, in_tokens + out_tokens))

        # Update persistent SQLite database
        try:
            with get_db() as conn:
                conn.execute("""
                INSERT INTO gemini_usage_log (stat_date, model_id, model_tier, input_tokens, output_tokens, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (now_date, model_id, tier, in_tokens, out_tokens, now_iso))

                # Also update general usage_stats summary
                conn.execute("""
                INSERT INTO usage_stats (stat_date, cloud_requests_count, cloud_estimated_input_tokens, cloud_estimated_output_tokens)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    cloud_requests_count = cloud_requests_count + 1,
                    cloud_estimated_input_tokens = cloud_estimated_input_tokens + excluded.cloud_estimated_input_tokens,
                    cloud_estimated_output_tokens = cloud_estimated_output_tokens + excluded.cloud_estimated_output_tokens;
                """, (now_date, in_tokens, out_tokens))
        except Exception as e:
            logger.debug(f"Failed to record call in gemini_usage_log: {e}")

    @classmethod
    async def acquire_permission(cls, model_id: str, estimated_tokens: int = 1000):
        """
        Guards before initiating API call.
        1. Checks Daily RPD cap. If exceeded, raises GeminiQuotaExceededError.
        2. Checks RPM / TPM sliding window. If near limit, sleeps to pace smoothly.
        """
        tier = cls.get_model_tier(model_id)
        config = cls.get_tier_config(model_id)
        
        # 1. Daily RPD Check
        daily = cls.get_daily_usage(tier)
        current_rpd = daily["requests_count"]
        if current_rpd >= config.rpd_cap:
            raise GeminiQuotaExceededError(
                f"Google Cloud Free Tier Daily Quota Exceeded for {config.tier_name} "
                f"({current_rpd}/{config.rpd_cap} Requests per Day per GCP project). "
                f"Switch to local models (MADLAD-400, Meta NLLB-200, or Qwen3 8B) or wait until 00:00 UTC.",
                model_id=model_id,
                tier=tier,
                current_rpd=current_rpd,
                max_rpd=config.rpd_cap
            )

        # 2. Sliding Window RPM and TPM Pacing
        async with cls._lock:
            now = time.time()
            cutoff = now - 60.0

            # Prune records older than 60 seconds
            history = cls._sliding_windows.setdefault(tier, [])
            cls._sliding_windows[tier] = [(ts, tok) for ts, tok in history if ts > cutoff]
            active_history = cls._sliding_windows[tier]

            # Calculate current in-window RPM and TPM
            current_rpm = len(active_history)
            current_tpm = sum(tok for _, tok in active_history)

            # If RPM cap reached, wait until oldest request slides out
            if current_rpm >= config.rpm_cap:
                oldest_ts = active_history[0][0]
                sleep_needed = max(0.1, (oldest_ts + 60.0) - now + 0.1)
                logger.info(
                    f"Gemini Guardrail: Pacing {model_id} request ({current_rpm}/{config.rpm_cap} RPM limit reached). "
                    f"Sleeping for {sleep_needed:.2f}s..."
                )
                await asyncio.sleep(sleep_needed)

            # If TPM cap reached, wait until tokens slide out
            elif current_tpm + estimated_tokens >= config.tpm_cap:
                oldest_ts = active_history[0][0]
                sleep_needed = max(0.1, (oldest_ts + 60.0) - now + 0.1)
                logger.info(
                    f"Gemini Guardrail: Pacing {model_id} request ({current_tpm}/{config.tpm_cap} TPM limit reached). "
                    f"Sleeping for {sleep_needed:.2f}s..."
                )
                await asyncio.sleep(sleep_needed)

            # Respect minimum inter-request spacing for safety
            elif active_history:
                last_ts = active_history[-1][0]
                elapsed_since_last = now - last_ts
                if elapsed_since_last < config.min_spacing_seconds:
                    spacing_wait = config.min_spacing_seconds - elapsed_since_last
                    await asyncio.sleep(spacing_wait)

    @classmethod
    def get_all_quotas_summary(cls) -> Dict[str, Any]:
        """Returns live telemetry of all Gemini tiers for UI telemetry bars & dashboards."""
        today = datetime.now().strftime("%Y-%m-%d")
        now = time.time()
        cutoff = now - 60.0

        summary = {
            "date": today,
            "tiers": {}
        }

        for tier_key, config in TIER_PROFILES.items():
            daily = cls.get_daily_usage(tier_key, today)
            rpd_used = daily["requests_count"]
            rpd_remaining = max(0, config.rpd_cap - rpd_used)
            pct_used = round((rpd_used / config.rpd_cap) * 100, 1)

            # Calculate active RPM & TPM in last 60s
            active = [(ts, tok) for ts, tok in cls._sliding_windows.get(tier_key, []) if ts > cutoff]
            rpm_active = len(active)
            tpm_active = sum(tok for _, tok in active)

            summary["tiers"][tier_key] = {
                "tier_name": config.tier_name,
                "rpm_cap": config.rpm_cap,
                "rpm_active": rpm_active,
                "tpm_cap": config.tpm_cap,
                "tpm_active": tpm_active,
                "rpd_cap": config.rpd_cap,
                "rpd_used": rpd_used,
                "rpd_remaining": rpd_remaining,
                "percentage_used": pct_used,
                "is_exhausted": rpd_used >= config.rpd_cap,
                "is_approaching_limit": pct_used >= 80.0
            }

        return summary
