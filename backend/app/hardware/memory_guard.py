import logging
from typing import Dict, Any, Tuple
from backend.app.hardware.monitor import HardwareMonitor

logger = logging.getLogger(__name__)

class MemorySafetyGuard:
    """
    Guards against memory exhaustion and OOM panics on Apple Silicon.
    Implements 16GB conservative limits and 32GB performance profile rules.
    """

    @classmethod
    def evaluate_model_fit(cls, required_ram_gb: float) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluates whether a model requiring `required_ram_gb` can be loaded safely.
        Returns: (can_load: bool, reason: str, metadata: dict)
        """
        hw = HardwareMonitor.get_hardware_status()
        available_gb = hw["available_ram_gb"]
        total_gb = hw["total_ram_gb"]
        pressure = hw["memory_pressure"]
        profile = hw["hardware_profile"]

        # Reserve safety headroom depending on total RAM
        headroom_gb = 3.0 if total_gb <= 18 else 5.0

        safe_capacity_gb = available_gb - headroom_gb

        if pressure == "RED":
            return False, f"Memory pressure is CRITICAL (RED). Available: {available_gb} GB. Free up memory before loading.", hw

        if required_ram_gb > (total_gb - 2.0):
            return False, f"Model requires ~{required_ram_gb} GB RAM, which exceeds physical system RAM ({total_gb} GB).", hw

        if required_ram_gb > safe_capacity_gb:
            if profile == "16GB_COMPATIBLE":
                return False, f"Model requires ~{required_ram_gb} GB, but safe capacity on 16GB profile is {round(safe_capacity_gb, 1)} GB (Headroom: {headroom_gb} GB). Use quantized model or Gemini.", hw
            else:
                return False, f"Model requires ~{required_ram_gb} GB, but available safe RAM is {round(safe_capacity_gb, 1)} GB.", hw

        return True, "Safe to load model.", hw

    @classmethod
    def get_runtime_throttle_policy(cls) -> Dict[str, Any]:
        """
        Returns throttling parameters for queue workers based on current memory pressure and hardware profile.
        """
        hw = HardwareMonitor.get_hardware_status()
        pressure = hw["memory_pressure"]
        profile = hw["hardware_profile"]

        if pressure == "RED":
            return {
                "action": "PAUSE",
                "max_concurrency": 0,
                "allow_secondary_model": False,
                "allow_reviewer_model": False,
                "reason": "Memory pressure is Critical (RED). Pausing new inference.",
                "profile": profile
            }
        elif pressure == "YELLOW":
            return {
                "action": "THROTTLE",
                "max_concurrency": 1,
                "allow_secondary_model": False,
                "allow_reviewer_model": False,
                "reason": "Memory pressure is Elevated (YELLOW). Limiting concurrency to 1 and disabling multi-model stacking.",
                "profile": profile
            }
        else:
            # GREEN
            if profile == "16GB_COMPATIBLE":
                return {
                    "action": "NORMAL_CONSERVATIVE",
                    "max_concurrency": 1,
                    "allow_secondary_model": False,  # sequential only
                    "allow_reviewer_model": True,     # sequential only
                    "reason": "16GB profile: Stable 1-model sequential operation.",
                    "profile": profile
                }
            else:
                return {
                    "action": "NORMAL_PERFORMANCE",
                    "max_concurrency": 2,
                    "allow_secondary_model": True,
                    "allow_reviewer_model": True,
                    "reason": "32GB profile: High-throughput performance mode active.",
                    "profile": profile
                }

    @classmethod
    def get_recommended_primary_model(cls) -> str:
        """Automatically selects genuinely compatible model based on physical RAM.
        NLLB-200 1.3B (CTranslate2 int8) is the safe, always-recommended default across
        all Apple Silicon profiles — MADLAD-400 7B is only used if a user explicitly
        downloads and selects it (huge ~14GB download, not auto-selected)."""
        return "nllb-200-distilled-1.3b"
