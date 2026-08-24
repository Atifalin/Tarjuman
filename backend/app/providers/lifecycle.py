import gc
import logging
from typing import Dict, Any, Optional
from backend.app.hardware.monitor import HardwareMonitor
from backend.app.hardware.memory_guard import MemorySafetyGuard

logger = logging.getLogger(__name__)

class ModelLifecycleManager:
    """
    Manages loading, health checks, execution batches, and safe unloading of models.
    Enforces 'One Large Model at a Time' on 16GB Macs and safe transitions on 32GB Macs.
    """

    _active_models: Dict[str, Any] = {}

    @classmethod
    def get_active_model_name(cls) -> Optional[str]:
        if not cls._active_models:
            return None
        return list(cls._active_models.keys())[0]

    @classmethod
    def ensure_single_model_resident(cls, new_model_id: str, estimated_ram_gb: float):
        """If on 16GB profile or memory pressure is high, unloads other models before loading new one."""
        hw = HardwareMonitor.get_hardware_status()
        profile = hw["hardware_profile"]
        
        if profile == "16GB_COMPATIBLE" or hw["memory_pressure"] in ["YELLOW", "RED"]:
            # Unload any previously cached models
            to_unload = [m for m in cls._active_models if m != new_model_id]
            for m in to_unload:
                cls.unload_model(m)

    @classmethod
    def unload_model(cls, model_id: str):
        if model_id in cls._active_models:
            logger.info(f"Unloading model {model_id} to release memory...")
            del cls._active_models[model_id]
            # Force garbage collection
            gc.collect()
            try:
                import torch
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except Exception:
                pass
            logger.info(f"Model {model_id} unloaded.")

    @classmethod
    def unload_all(cls):
        models = list(cls._active_models.keys())
        for m in models:
            cls.unload_model(m)
