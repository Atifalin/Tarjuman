from fastapi import APIRouter
from backend.app.hardware.monitor import HardwareMonitor
from backend.app.hardware.memory_guard import MemorySafetyGuard
from backend.app.workers.orchestrator import ServerActivityTracker

router = APIRouter(prefix="/api/hardware", tags=["Hardware"])

@router.get("/status")
def get_hardware_status():
    """Returns complete real-time macOS hardware status, unified RAM, memory pressure, and server activity."""
    hw = HardwareMonitor.get_hardware_status()
    throttle = MemorySafetyGuard.get_runtime_throttle_policy()
    activity = ServerActivityTracker.get_state()
    return {
        "metrics": hw,
        "throttle_policy": throttle,
        "server_activity": activity
    }

@router.get("/evaluate-model/{ram_req_gb}")
def evaluate_model_fit(ram_req_gb: float):
    """Evaluates if a model with given RAM footprint can be safely loaded right now."""
    can_load, reason, meta = MemorySafetyGuard.evaluate_model_fit(ram_req_gb)
    return {
        "can_load": can_load,
        "reason": reason,
        "meta": meta
    }
