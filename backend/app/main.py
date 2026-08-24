import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.database.connection import init_db
from backend.app.api.hardware_routes import router as hardware_router
from backend.app.api.provider_routes import router as provider_router
from backend.app.api.project_routes import router as project_router
from backend.app.api.review_routes import router as review_router
from backend.app.api.glossary_routes import router as glossary_router
from backend.app.api.benchmark_routes import router as benchmark_router
from backend.app.api.export_routes import router as export_router
from backend.app.api.system_routes import router as system_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("tarjuman")

def _try_autostart_mlx_server():
    """
    If the Qari-OCR MLX model has already been installed (on this or a previous run),
    make sure the local mlx-vlm OpenAI-compatible server is running. Best-effort and
    non-blocking so it never prevents the backend from starting (e.g. on non-Apple-Silicon
    or machines where MLX hasn't been installed yet).
    """
    import socket
    import subprocess
    model_dir = settings.MODELS_DIR / "qari-ocr-0.4.0-mlx-4bit"
    if not model_dir.exists():
        return
    try:
        port = int(settings.MLX_VLM_BASE_URL.rstrip("/").rsplit(":", 1)[-1].split("/")[0])
    except ValueError:
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    already_running = s.connect_ex(("127.0.0.1", port)) == 0
    s.close()
    if already_running:
        logger.info("MLX-VLM server already running.")
        return

    try:
        subprocess.Popen(
            [sys.executable, "-m", "mlx_vlm.server", "--model", str(model_dir), "--port", str(port), "--host", "127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info(f"Auto-started MLX-VLM server on port {port} for Qari-OCR.")
    except Exception as e:
        logger.warning(f"Could not auto-start MLX-VLM server: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION} (Env: {settings.APP_ENV})...")
    init_db()
    _try_autostart_mlx_server()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Local Arabic -> Urdu Translation Workstation for Apple Silicon Macs",
    lifespan=lifespan
)

# Enable CORS for local Vite dev server and desktop shells
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from backend.app.providers.gemini_guardrails import GeminiQuotaExceededError
from backend.app.workers.orchestrator import ServerActivityTracker

# Register API Routers
app.include_router(hardware_router)
app.include_router(provider_router)
app.include_router(project_router)
app.include_router(review_router)
app.include_router(glossary_router)
app.include_router(benchmark_router)
app.include_router(export_router)
app.include_router(system_router)

@app.exception_handler(GeminiQuotaExceededError)
async def gemini_quota_exception_handler(request, exc: GeminiQuotaExceededError):
    ServerActivityTracker.set_error(str(exc))
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc), "error_type": "QUOTA_EXCEEDED"}
    )

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "status": "operational",
        "description": "Mac-first Local Arabic -> Urdu Document Translation Workstation"
    }
