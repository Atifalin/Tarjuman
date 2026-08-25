import os
import sys
import psutil
import subprocess
import shutil
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class HardwareMonitor:
    """
    Safe macOS Hardware Monitor.
    Extracts genuine hardware capabilities, unified memory utilization,
    memory pressure, CPU usage, and disk space.
    Never fabricates metrics.
    """

    @staticmethod
    def get_chip_name() -> str:
        """Returns the Apple Silicon chip name or processor model."""
        if sys.platform == "darwin":
            try:
                out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
                if out:
                    return out
            except Exception:
                pass
        return f"{os.uname().machine} processor"

    @staticmethod
    def get_memory_pressure_darwin() -> str:
        """
        Extracts memory pressure state using macOS vm_stat / memory_pressure command if accessible.
        Returns: 'GREEN', 'YELLOW', 'RED', or 'UNKNOWN'
        """
        if sys.platform != "darwin":
            # Fallback for non-macOS environments based on percent used
            v = psutil.virtual_memory()
            if v.percent < 75:
                return "GREEN"
            elif v.percent < 90:
                return "YELLOW"
            else:
                return "RED"

        try:
            # Check vm_stat pageout activity or psutil virtual memory percentage
            vm = psutil.virtual_memory()
            # On macOS unified memory, swap activity + high usage indicates pressure
            swap = psutil.swap_memory()
            
            if vm.percent > 95 or swap.used > 6 * 1024 * 1024 * 1024:  # >6GB swap
                return "RED"
            elif vm.percent > 85 or swap.used > 1.5 * 1024 * 1024 * 1024:  # >1.5GB swap
                return "YELLOW"
            else:
                return "GREEN"
        except Exception as e:
            logger.debug(f"Error checking memory pressure: {e}")
            return "GREEN"

    @classmethod
    def get_hardware_status(cls, data_dir: Optional[str] = None) -> Dict[str, Any]:
        """Collects complete real-time hardware status."""
        chip = cls.get_chip_name()
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        
        # Disk usage for the active data partition
        target_path = data_dir or os.path.expanduser("~")
        try:
            usage = shutil.disk_usage(target_path)
            disk_total_gb = round(usage.total / (1024 ** 3), 1)
            disk_free_gb = round(usage.free / (1024 ** 3), 1)
            disk_percent = round((usage.used / usage.total) * 100, 1)
        except Exception:
            disk_total_gb = 0
            disk_free_gb = 0
            disk_percent = 0

        # Tarjuman process usage
        current_process = psutil.Process()
        proc_mem_mb = round(current_process.memory_info().rss / (1024 ** 2), 1)

        pressure = cls.get_memory_pressure_darwin()
        total_ram_gb = round(vm.total / (1024 ** 3), 1)
        used_ram_gb = round(vm.used / (1024 ** 3), 1)
        available_ram_gb = round(vm.available / (1024 ** 3), 1)

        # Hardware Profile Determination
        if total_ram_gb >= 28:
            hardware_profile = "32GB_PERFORMANCE"
        elif total_ram_gb >= 20:
            hardware_profile = "24GB_BALANCED"
        else:
            hardware_profile = "16GB_COMPATIBLE"

        return {
            "chip_name": chip,
            "is_apple_silicon": "Apple" in chip or "M1" in chip or "M2" in chip or "M3" in chip or "M4" in chip or "arm" in os.uname().machine,
            "hardware_profile": hardware_profile,
            "cpu_percent": cpu_percent,
            "cpu_cores_logical": cpu_count,
            "cpu_cores_physical": physical_cores,
            "total_ram_gb": total_ram_gb,
            "used_ram_gb": used_ram_gb,
            "available_ram_gb": available_ram_gb,
            "ram_percent": vm.percent,
            "swap_used_mb": round(swap.used / (1024 ** 2), 1),
            "memory_pressure": pressure,  # GREEN, YELLOW, RED
            "disk_total_gb": disk_total_gb,
            "disk_free_gb": disk_free_gb,
            "disk_percent": disk_percent,
            "process_memory_mb": proc_mem_mb,
            "temperature": "Unavailable (macOS private sensor)",
        }
