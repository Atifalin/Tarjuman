import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Tarjuman"
    APP_ENV: str = os.getenv("APP_ENV", "production")  # production, development, test
    VERSION: str = "1.0.0"
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path(os.getenv("TARJUMAN_DATA_DIR", str(Path(__file__).resolve().parent.parent.parent / "data")))
    
    @property
    def DATABASE_PATH(self) -> Path:
        return self.DATA_DIR / "tarjuman.sqlite"
    
    # Provider API Endpoints
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    LMSTUDIO_BASE_URL: str = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    MLX_VLM_BASE_URL: str = os.getenv("MLX_VLM_BASE_URL", "http://127.0.0.1:8082/v1")
    MLX_OCR_MODEL_NAME: str = os.getenv("MLX_OCR_MODEL_NAME", "qari-ocr-0.4.0-mlx-4bit")

    # Local model weights folder (GGUF / CTranslate2 / MLX). Defaults to a portable
    # in-repo folder so a fresh clone on any M2+/16GB+ Mac works out of the box.
    # Point TARJUMAN_MODELS_DIR at an external SSD if you want downloads stored there.
    MODELS_DIR: Path = Path(os.getenv("TARJUMAN_MODELS_DIR", "data/models"))
    
    # Cloud Configuration (Optional)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Memory safety thresholds (MB)
    HEADROOM_16GB_MB: int = 3072  # 3GB headroom
    HEADROOM_32GB_MB: int = 5120  # 5GB headroom
    
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

# Persisted runtime overrides (e.g. a custom models folder chosen in the Settings UI,
# such as an external SSD). Stored outside of env vars so it survives across app restarts
# without needing to re-export TARJUMAN_MODELS_DIR every time.
RUNTIME_CONFIG_PATH = Path("data/tarjuman_runtime.json")

def _load_runtime_overrides():
    if not RUNTIME_CONFIG_PATH.exists():
        return
    try:
        import json
        data = json.loads(RUNTIME_CONFIG_PATH.read_text())
        models_dir = data.get("models_dir")
        if models_dir:
            settings.MODELS_DIR = Path(models_dir).expanduser()
    except Exception:
        pass  # Never block startup on a corrupt/missing override file

_load_runtime_overrides()
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
