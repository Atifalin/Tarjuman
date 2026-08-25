import os
import sys
import platform
import asyncio
import logging
import subprocess
import shutil
import httpx
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.security import CredentialManager

from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["System & Dependencies"])

ARGOS_DATA_DIR = (Path(__file__).resolve().parent.parent.parent.parent / "data" / "argos_data")
ARGOS_DATA_DIR.mkdir(parents=True, exist_ok=True)

# NLLB-200 1.3B (CTranslate2) & Qari-OCR-0.4.0 (MLX) install targets
NLLB_HF_REPO = "facebook/nllb-200-distilled-1.3B"
NLLB_CT2_DIRNAME = "nllb-200-1.3b"
# NAMAA-Space only publishes a PEFT LoRA adapter (not a merged model), fine-tuned on top
# of this base — it must be merged before it can be converted to a standalone MLX model.
QARI_OCR_BASE_REPO = "unsloth/Qwen3-VL-4B-Instruct"
QARI_OCR_HF_REPO = "NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct"
QARI_OCR_MLX_DIRNAME = "qari-ocr-0.4.0-mlx-4bit"
QARI_OCR_MERGED_DIRNAME = "_qari-ocr-0.4.0-merged-tmp"

# Global tracker for background install jobs
INSTALL_STATE: Dict[str, Any] = {
    "status": "idle",  # "idle" | "installing" | "completed" | "failed"
    "target": None,
    "logs": "",
    "error": None
}

# Handle to the background MLX-VLM server subprocess (if we started it)
MLX_SERVER_PROCESS: Optional[subprocess.Popen] = None


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _models_dir() -> Path:
    settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.MODELS_DIR.resolve()


def _mlx_server_port() -> str:
    return settings.MLX_VLM_BASE_URL.rstrip("/").rsplit(":", 1)[-1].split("/")[0]


def _start_mlx_server_process(model_dir: Path) -> Dict[str, Any]:
    global MLX_SERVER_PROCESS
    if MLX_SERVER_PROCESS is not None and MLX_SERVER_PROCESS.poll() is None:
        return {"success": True, "message": "MLX-VLM server already running."}

    port = _mlx_server_port()
    try:
        MLX_SERVER_PROCESS = subprocess.Popen(
            [sys.executable, "-m", "mlx_vlm.server", "--model", str(model_dir), "--port", port, "--host", "127.0.0.1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"success": True, "message": f"Started MLX-VLM server on port {port} (PID {MLX_SERVER_PROCESS.pid})."}
    except Exception as e:
        return {"success": False, "message": f"Failed to start MLX-VLM server: {str(e)}"}

class PullModelRequest(BaseModel):
    model_name: str = "qwen3:8b"

@router.get("/dependencies")
async def get_dependencies_status():
    """
    Returns live dependency status for PyTorch, Transformers, Apple Silicon MPS, Ollama, and Gemini.
    """
    # 1. PyTorch & Transformers
    torch_installed = False
    torch_version = None
    transformers_installed = False
    transformers_version = None
    mps_available = False
    
    try:
        import torch
        torch_installed = True
        torch_version = torch.__version__
        mps_available = torch.backends.mps.is_available()
    except Exception:
        pass

    try:
        import transformers
        transformers_installed = True
        transformers_version = transformers.__version__
    except Exception:
        pass

    # 2. Argos Translate
    argos_installed = False
    argos_version = None
    argos_packages_installed = False
    argos_languages = []
    try:
        import ctranslate2
        import sentencepiece
        argos_installed = True
        argos_version = getattr(ctranslate2, "__version__", "ctranslate2")
        
        ar_en_ready = (ARGOS_DATA_DIR / "packages" / "ar_en" / "model").exists()
        en_ur_ready = (ARGOS_DATA_DIR / "packages" / "en_ur" / "model").exists()
        argos_packages_installed = ar_en_ready and en_ur_ready
        if argos_packages_installed:
            argos_languages = ["ar", "en", "ur"]
    except Exception:
        pass

    # 3. Ollama
    ollama_running = False
    ollama_models = []
    ollama_url = settings.OLLAMA_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{ollama_url}/api/tags")
            if res.status_code == 200:
                ollama_running = True
                ollama_models = [m.get("name") for m in res.json().get("models", [])]
    except Exception:
        pass

    # 4. Gemini Key
    gemini_key = CredentialManager.get_gemini_api_key()

    # 5. Overall Model Readiness Matrix
    # Argos Translate
    argos_ready = argos_installed and argos_packages_installed
    if not argos_installed:
        argos_reason = "argostranslate Python library not installed"
    elif not argos_packages_installed:
        argos_reason = "Missing Arabic/Urdu offline language packages (~90MB)"
    else:
        argos_reason = "READY (100% Offline CTranslate2 ar -> en -> ur)"

    # MADLAD-400 (transformers/pytorch)
    madlad_weights_exist = Path("data/models/madlad400-7b").exists()
    madlad_ready = madlad_weights_exist and torch_installed and transformers_installed
    if not (torch_installed and transformers_installed):
        madlad_reason = "PyTorch or Transformers not installed"
    elif not madlad_weights_exist:
        madlad_reason = "Model weights not downloaded (~14 GB)"
    else:
        madlad_reason = "READY (Local MPS/CPU)"

    # Meta NLLB-200 1.3B (CTranslate2 int8, the recommended default)
    nllb_13b_dir_exists = (_models_dir() / NLLB_CT2_DIRNAME / "model.bin").exists()
    nllb_13b_ready = nllb_13b_dir_exists
    if nllb_13b_dir_exists:
        nllb_13b_reason = "READY (CTranslate2 int8, Direct ar → ur, native Apple Silicon)"
    elif not (torch_installed and transformers_installed):
        nllb_13b_reason = "Click 'Install NLLB-200 1.3B' to download & convert (~2.6 GB)"
    else:
        nllb_13b_reason = "CTranslate2 weights not downloaded yet (click Install NLLB-200 1.3B)"

    # Qari-OCR-0.4.0 (native MLX Arabic OCR)
    mlx_installed = False
    mlx_vlm_installed = False
    try:
        import mlx.core  # noqa: F401
        mlx_installed = True
    except Exception:
        pass
    try:
        import mlx_vlm  # noqa: F401
        mlx_vlm_installed = True
    except Exception:
        pass

    qari_weights_exist = (_models_dir() / QARI_OCR_MLX_DIRNAME).exists()
    mlx_server_running = False
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{settings.MLX_VLM_BASE_URL.rstrip('/')}/models")
            mlx_server_running = res.status_code == 200
    except Exception:
        pass

    if not _is_apple_silicon():
        qari_ready = False
        qari_reason = "Requires an Apple Silicon (M-series) Mac"
    elif not (mlx_installed and mlx_vlm_installed):
        qari_ready = False
        qari_reason = "mlx / mlx-vlm not installed yet (click Install Qari-OCR MLX)"
    elif not qari_weights_exist:
        qari_ready = False
        qari_reason = "Model weights not downloaded/converted yet (~2.5 GB)"
    elif not mlx_server_running:
        qari_ready = False
        qari_reason = "MLX-VLM server not running (click Start Server)"
    else:
        qari_ready = True
        qari_reason = "READY (Native MLX, Apple Silicon GPU)"

    # Qwen2-VL (ollama vision OCR)
    qwen_vl_installed = any("qwen2-vl" in m or "qwen-vl" in m for m in ollama_models) if ollama_running else False
    if not ollama_running:
        qwen_vl_ready = False
        qwen_vl_reason = "Ollama is not running"
    elif not qwen_vl_installed:
        qwen_vl_ready = False
        qwen_vl_reason = "Model not pulled (run ollama pull qwen2-vl:7b)"
    else:
        qwen_vl_ready = True
        qwen_vl_reason = "READY (Local Vision-Language OCR)"

    # Qwen3 8B (ollama)
    qwen3_installed = any("qwen3" in m or "qwen2.5" in m for m in ollama_models) if ollama_running else False
    if not ollama_running:
        qwen3_ready = False
        qwen3_reason = "Ollama is not running"
    elif not qwen3_installed:
        qwen3_ready = False
        qwen3_reason = "Model not pulled in Ollama"
    else:
        qwen3_ready = True
        qwen3_reason = "READY"

    # Gemini 3.6 Flash (cloud)
    gemini_ready = bool(gemini_key)
    gemini_reason = "READY" if gemini_ready else "API Key not configured"

    # Apple Native Translation (ar -> en Bridge)
    apple_ready = sys.platform == "darwin"
    apple_reason = "READY (ar -> en Reference Bridge on Apple Neural Engine)"

    return {
        "pytorch": {
            "installed": torch_installed,
            "torch_version": torch_version,
            "transformers_installed": transformers_installed,
            "transformers_version": transformers_version,
            "mps_available": mps_available,
            "device": "mps (Apple Silicon GPU)" if mps_available else ("cpu" if torch_installed else "none")
        },
        "argos": {
            "installed": argos_installed,
            "version": argos_version,
            "packages_installed": argos_packages_installed,
            "languages": argos_languages
        },
        "ollama": {
            "running": ollama_running,
            "endpoint": ollama_url,
            "installed_models": ollama_models,
            "qwen3_installed": qwen3_installed
        },
        "gemini": {
            "configured": gemini_ready
        },
        "mlx": {
            "installed": mlx_installed and mlx_vlm_installed,
            "weights_exist": qari_weights_exist,
            "server_running": mlx_server_running,
            "is_apple_silicon": _is_apple_silicon()
        },
        "readiness_matrix": {
            "argos-translate": {"ready": argos_ready, "status": "READY" if argos_ready else "NOT_INSTALLED", "reason": argos_reason},
            "apple-native-translation": {"ready": apple_ready, "status": "READY (ar -> en)", "reason": apple_reason},
            "qwen2-vl:7b": {"ready": qwen_vl_ready, "status": "READY" if qwen_vl_ready else ("NOT_CONNECTED" if not ollama_running else "NOT_INSTALLED"), "reason": qwen_vl_reason},
            "madlad400-7b-mt": {"ready": madlad_ready, "status": "READY" if madlad_ready else "NOT_INSTALLED", "reason": madlad_reason},
            "nllb-200-distilled-1.3b": {"ready": nllb_13b_ready, "status": "READY" if nllb_13b_ready else "NOT_INSTALLED", "reason": nllb_13b_reason},
            "qari-ocr-0.4.0-vl-4b": {"ready": qari_ready, "status": "READY" if qari_ready else "NOT_INSTALLED", "reason": qari_reason},
            "qwen3:8b": {"ready": qwen3_ready, "status": "READY" if qwen3_ready else ("NOT_CONNECTED" if not ollama_running else "NOT_INSTALLED"), "reason": qwen3_reason},
            "gemini-3.6-flash": {"ready": gemini_ready, "status": "READY" if gemini_ready else "NOT_CONFIGURED", "reason": gemini_reason},
            "gemini-3.6-pro": {"ready": gemini_ready, "status": "READY" if gemini_ready else "NOT_CONFIGURED", "reason": gemini_reason}
        },
        "install_state": INSTALL_STATE
    }

def _run_pip_install():
    global INSTALL_STATE
    INSTALL_STATE["status"] = "installing"
    INSTALL_STATE["target"] = "pytorch"
    INSTALL_STATE["logs"] = "Starting PyTorch and Transformers installation for Apple Silicon...\n"
    INSTALL_STATE["error"] = None

    python_bin = sys.executable
    pip_cmd = [
        python_bin, "-m", "pip", "install", "--upgrade",
        "torch", "torchvision", "torchaudio",
        "transformers", "sentencepiece", "accelerate"
    ]

    try:
        INSTALL_STATE["logs"] += f"Executing: {' '.join(pip_cmd)}\n"
        proc = subprocess.Popen(
            pip_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
            if len(INSTALL_STATE["logs"]) > 20000:
                INSTALL_STATE["logs"] = INSTALL_STATE["logs"][-15000:]

        proc.stdout.close()
        return_code = proc.wait()

        if return_code == 0:
            INSTALL_STATE["status"] = "completed"
            INSTALL_STATE["logs"] += "\n✅ PyTorch and Transformers installation completed successfully!\n"
        else:
            INSTALL_STATE["status"] = "failed"
            INSTALL_STATE["error"] = f"Pip exited with return code {return_code}"
            INSTALL_STATE["logs"] += f"\n❌ Installation failed with exit code {return_code}\n"
    except Exception as e:
        INSTALL_STATE["status"] = "failed"
        INSTALL_STATE["error"] = str(e)
        INSTALL_STATE["logs"] += f"\n❌ Installation exception: {str(e)}\n"

@router.post("/install-pytorch")
async def install_pytorch(background_tasks: BackgroundTasks):
    """
    Installs Apple Silicon/MPS compatible PyTorch, Transformers, SentencePiece, and Accelerate in the active Python environment.
    """
    global INSTALL_STATE
    if INSTALL_STATE["status"] == "installing":
        return {"success": False, "message": "An installation is already in progress.", "status": INSTALL_STATE}

    background_tasks.add_task(_run_pip_install)
    return {"success": True, "message": "PyTorch installation started in background.", "status": INSTALL_STATE}

@router.get("/install-status")
def get_install_status():
    return INSTALL_STATE

def _run_argos_install():
    global INSTALL_STATE
    INSTALL_STATE["status"] = "installing"
    INSTALL_STATE["target"] = "argos"
    INSTALL_STATE["logs"] = "Step 1/3: Installing argostranslate Python library via pip...\n"
    INSTALL_STATE["error"] = None

    python_bin = sys.executable
    pip_cmd = [python_bin, "-m", "pip", "install", "--upgrade", "argostranslate"]

    try:
        INSTALL_STATE["logs"] += f"Executing: {' '.join(pip_cmd)}\n"
        proc = subprocess.Popen(
            pip_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
            if len(INSTALL_STATE["logs"]) > 20000:
                INSTALL_STATE["logs"] = INSTALL_STATE["logs"][-15000:]

        proc.stdout.close()
        return_code = proc.wait()

        if return_code != 0:
            INSTALL_STATE["status"] = "failed"
            INSTALL_STATE["error"] = f"Pip install argostranslate failed (exit code {return_code})"
            INSTALL_STATE["logs"] += f"\n❌ Pip install failed with exit code {return_code}\n"
            return

        INSTALL_STATE["logs"] += "\nStep 2/3: Fetching Argos Translate package index...\n"
        import urllib.request
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')]
        urllib.request.install_opener(opener)

        import argostranslate.settings
        argostranslate.settings.data_dir = ARGOS_DATA_DIR
        argostranslate.settings.cache_dir = ARGOS_DATA_DIR
        argostranslate.settings.package_dirs = [ARGOS_DATA_DIR / "packages"]
        argostranslate.settings.local_package_index = ARGOS_DATA_DIR / "index.json"
        
        import argostranslate.package
        import argostranslate.translate

        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()

        INSTALL_STATE["logs"] += "Step 3/3: Downloading offline language models (~90 MB total)...\n"

        def _download_with_progress(url: str, dest: Path, model_label: str):
            req_headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
            INSTALL_STATE["logs"] += f"Downloading {model_label} from {url}...\n"
            with httpx.Client(timeout=180.0, follow_redirects=True, headers=req_headers) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    tot = int(resp.headers.get("Content-Length", 0))
                    done = 0
                    last_rep = 0
                    with open(dest, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=524288):
                            f.write(chunk)
                            done += len(chunk)
                            if done - last_rep > 5 * 1024 * 1024 or (tot and done >= tot):
                                pct = int(done / tot * 100) if tot else 0
                                mb_done = done / (1024 * 1024)
                                mb_tot = tot / (1024 * 1024)
                                INSTALL_STATE["logs"] += f"  [{model_label}] {mb_done:.1f} MB / {mb_tot:.1f} MB ({pct}%)\n"
                                last_rep = done

        # 1. Download Arabic -> English (~45 MB)
        pkg_ar_en = next((p for p in available_packages if p.from_code == "ar" and p.to_code == "en"), None)
        if pkg_ar_en and pkg_ar_en.links:
            dl_url = pkg_ar_en.links[0]
            dest_file = ARGOS_DATA_DIR / "translate-ar_en.argosmodel"
            _download_with_progress(dl_url, dest_file, "Arabic → English")
            INSTALL_STATE["logs"] += "Installing Arabic → English model into local package store...\n"
            argostranslate.package.install_from_path(dest_file)
            INSTALL_STATE["logs"] += "✓ Arabic → English model installed successfully.\n"
        else:
            INSTALL_STATE["logs"] += "Notice: ar_en package already installed or not found.\n"

        # 2. Download English -> Urdu (~45 MB)
        pkg_en_ur = next((p for p in available_packages if p.from_code == "en" and p.to_code == "ur"), None)
        if pkg_en_ur and pkg_en_ur.links:
            dl_url = pkg_en_ur.links[0]
            dest_file = ARGOS_DATA_DIR / "translate-en_ur.argosmodel"
            _download_with_progress(dl_url, dest_file, "English → Urdu")
            INSTALL_STATE["logs"] += "Installing English → Urdu model into local package store...\n"
            argostranslate.package.install_from_path(dest_file)
            INSTALL_STATE["logs"] += "✓ English → Urdu model installed successfully.\n"
        else:
            INSTALL_STATE["logs"] += "Notice: en_ur package already installed or not found.\n"

        INSTALL_STATE["status"] = "completed"
        INSTALL_STATE["logs"] += "\n✅ Argos Translate and offline Arabic/Urdu models installed successfully! Ready for 100% offline translation.\n"
    except Exception as e:
        INSTALL_STATE["status"] = "failed"
        INSTALL_STATE["error"] = str(e)
        INSTALL_STATE["logs"] += f"\n❌ Argos installation exception: {str(e)}\n"

@router.post("/install-argos")
async def install_argos(background_tasks: BackgroundTasks):
    """
    Installs argostranslate and downloads Arabic-English and English-Urdu offline model packages (~90MB).
    """
    global INSTALL_STATE
    if INSTALL_STATE["status"] == "installing":
        return {"success": False, "message": "An installation is already in progress.", "status": INSTALL_STATE}

    background_tasks.add_task(_run_argos_install)
    return {"success": True, "message": "Argos Translate installation started in background.", "status": INSTALL_STATE}

@router.post("/verify-argos")
def verify_argos():
    """
    Performs real live check of Argos Translate library and installed language packages.
    """
    try:
        import ctranslate2
        import sentencepiece
        
        ar_en_ready = (ARGOS_DATA_DIR / "packages" / "ar_en" / "model").exists()
        en_ur_ready = (ARGOS_DATA_DIR / "packages" / "en_ur" / "model").exists()
        ready = ar_en_ready and en_ur_ready
        
        return {
            "success": ready,
            "installed": True,
            "packages_installed": ready,
            "languages": ["ar", "en", "ur"] if ready else [],
            "message": "Argos Translate is verified and ready (100% Offline CTranslate2 ar -> en -> ur)." if ready else "Argos models (ar_en or en_ur) not found in local package directory."
        }
    except ImportError as e:
        return {
            "success": False,
            "installed": False,
            "packages_installed": False,
            "error": str(e),
            "message": f"CTranslate2 or SentencePiece is not installed: {str(e)}"
        }

@router.post("/verify-pytorch")
def verify_pytorch():
    """
    Performs real live check: import torch, check MPS acceleration, and check transformers.
    """
    try:
        import torch
        has_mps = torch.backends.mps.is_available()
        v = torch.__version__
        
        import transformers
        tv = transformers.__version__
        
        return {
            "success": True,
            "installed": True,
            "mps_available": has_mps,
            "torch_version": v,
            "transformers_version": tv,
            "message": f"PyTorch {v} verified. Apple Silicon MPS acceleration: {'✓ ENABLED' if has_mps else 'CPU mode'}."
        }
    except ImportError as e:
        return {
            "success": False,
            "installed": False,
            "mps_available": False,
            "error": str(e),
            "message": f"PyTorch is not installed: {str(e)}"
        }

def _run_nllb_install():
    global INSTALL_STATE
    INSTALL_STATE["status"] = "installing"
    INSTALL_STATE["target"] = "nllb"
    INSTALL_STATE["logs"] = "Step 1/2: Installing transformers, sentencepiece, ctranslate2...\n"
    INSTALL_STATE["error"] = None

    python_bin = sys.executable
    out_dir = _models_dir() / NLLB_CT2_DIRNAME
    env = os.environ.copy()
    env["HF_HOME"] = str(_models_dir() / ".hf_cache")

    try:
        pip_cmd = [python_bin, "-m", "pip", "install", "--upgrade", "transformers", "sentencepiece", "ctranslate2"]
        INSTALL_STATE["logs"] += f"Executing: {' '.join(pip_cmd)}\n"
        proc = subprocess.Popen(pip_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
        proc.stdout.close()
        if proc.wait() != 0:
            raise RuntimeError("pip install failed for transformers/sentencepiece/ctranslate2")

        INSTALL_STATE["logs"] += f"\nStep 2/2: Downloading & converting {NLLB_HF_REPO} to CTranslate2 int8 (~2.6 GB, can take several minutes)...\n"
        convert_cmd = [
            python_bin, "-m", "ctranslate2.converters.transformers",
            "--model", NLLB_HF_REPO,
            "--output_dir", str(out_dir),
            "--quantization", "int8",
            "--force"
        ]
        INSTALL_STATE["logs"] += f"Executing: {' '.join(convert_cmd)}\n"
        proc = subprocess.Popen(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
            if len(INSTALL_STATE["logs"]) > 20000:
                INSTALL_STATE["logs"] = INSTALL_STATE["logs"][-15000:]
        proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ctranslate2 conversion exited with code {rc}")

        INSTALL_STATE["logs"] += "\nCaching tokenizer files into the model directory...\n"
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(NLLB_HF_REPO, src_lang="arb_Arab", cache_dir=env["HF_HOME"])
        tok.save_pretrained(str(out_dir))

        INSTALL_STATE["status"] = "completed"
        INSTALL_STATE["logs"] += f"\n✅ NLLB-200 1.3B installed at {out_dir} (CTranslate2 int8, direct Arabic → Urdu, no MLX seq2seq runtime exists so this is the fastest native Apple Silicon option).\n"
    except Exception as e:
        INSTALL_STATE["status"] = "failed"
        INSTALL_STATE["error"] = str(e)
        INSTALL_STATE["logs"] += f"\n❌ NLLB-200 1.3B installation exception: {str(e)}\n"

@router.post("/install-nllb")
async def install_nllb(background_tasks: BackgroundTasks):
    """
    Downloads facebook/nllb-200-distilled-1.3B and converts it to a quantized (int8)
    CTranslate2 model for fast, accurate, direct Arabic -> Urdu translation.
    """
    global INSTALL_STATE
    if INSTALL_STATE["status"] == "installing":
        return {"success": False, "message": "An installation is already in progress.", "status": INSTALL_STATE}

    background_tasks.add_task(_run_nllb_install)
    return {"success": True, "message": "NLLB-200 1.3B download & CTranslate2 conversion started in background.", "status": INSTALL_STATE}


_QARI_MERGE_SCRIPT = """
import sys
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor
from peft import PeftModel

base_repo = sys.argv[1]
adapter_repo = sys.argv[2]
out_dir = sys.argv[3]

print(f"Loading base model {base_repo} (fp16)...", flush=True)
base = AutoModelForImageTextToText.from_pretrained(base_repo, torch_dtype=torch.float16, low_cpu_mem_usage=True)

print(f"Applying Qari-OCR LoRA adapter {adapter_repo}...", flush=True)
model = PeftModel.from_pretrained(base, adapter_repo)

print("Merging adapter weights into base model...", flush=True)
merged = model.merge_and_unload()
merged.save_pretrained(out_dir, safe_serialization=True)

print("Saving processor/tokenizer...", flush=True)
processor = AutoProcessor.from_pretrained(adapter_repo)
processor.save_pretrained(out_dir)

# mlx-vlm (0.6.15) expects the old flat `rope_theta` / `rope_scaling` fields on text_config,
# but recent transformers versions nest them under `rope_parameters` instead. Patch the saved
# config.json so mlx_vlm.convert can parse it.
print("Patching config.json for mlx-vlm compatibility (rope_parameters -> rope_theta/rope_scaling)...", flush=True)
import json
import os as _os
config_path = _os.path.join(out_dir, "config.json")
with open(config_path) as f:
    cfg = json.load(f)
text_cfg = cfg.get("text_config", cfg)
rope_params = text_cfg.get("rope_parameters")
if rope_params and "rope_theta" not in text_cfg:
    text_cfg["rope_theta"] = rope_params.get("rope_theta", 5000000)
    text_cfg["rope_scaling"] = {
        "type": rope_params.get("rope_type", "default"),
        "mrope_section": rope_params.get("mrope_section", [24, 20, 20]),
    }
# mlx-vlm 0.6.15 only recognizes the older "qwen3_vl"/"qwen3_5*" vision model_type strings;
# recent transformers renamed the vision sub-config's model_type to "qwen3_vl_vision".
vision_cfg = cfg.get("vision_config")
if vision_cfg and vision_cfg.get("model_type") == "qwen3_vl_vision":
    vision_cfg["model_type"] = "qwen3_vl"
with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2)

print("MERGE_COMPLETE", flush=True)
"""


def _run_mlx_ocr_install():
    global INSTALL_STATE
    INSTALL_STATE["status"] = "installing"
    INSTALL_STATE["target"] = "mlx_ocr"
    INSTALL_STATE["logs"] = "Step 1/3: Installing mlx, mlx-vlm, peft, transformers, accelerate...\n"
    INSTALL_STATE["error"] = None

    if not _is_apple_silicon():
        INSTALL_STATE["status"] = "failed"
        INSTALL_STATE["error"] = "MLX requires an Apple Silicon (arm64) Mac."
        INSTALL_STATE["logs"] += "\n❌ This machine is not Apple Silicon. MLX is unavailable here.\n"
        return

    python_bin = sys.executable
    out_dir = _models_dir() / QARI_OCR_MLX_DIRNAME
    merged_dir = _models_dir() / QARI_OCR_MERGED_DIRNAME
    env = os.environ.copy()
    env["HF_HOME"] = str(_models_dir() / ".hf_cache")

    try:
        pip_cmd = [python_bin, "-m", "pip", "install", "--upgrade", "mlx", "mlx-vlm", "peft", "transformers", "accelerate", "torchvision"]
        INSTALL_STATE["logs"] += f"Executing: {' '.join(pip_cmd)}\n"
        proc = subprocess.Popen(pip_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
        proc.stdout.close()
        if proc.wait() != 0:
            raise RuntimeError("pip install failed for mlx/mlx-vlm/peft")

        # NAMAA-Space only ships a PEFT LoRA adapter for 0.4.0, not a merged model — merge it
        # into the base Qwen3-VL-4B-Instruct first so mlx_vlm.convert has a real config.json
        # and full weights to work with.
        INSTALL_STATE["logs"] += (
            f"\nStep 2/3: Downloading base model ({QARI_OCR_BASE_REPO}, ~8 GB fp16) and merging "
            f"the Qari-OCR-0.4.0 LoRA adapter into it (NAMAA-Space only publishes the adapter, not a merged model)...\n"
        )
        merge_cmd = [python_bin, "-c", _QARI_MERGE_SCRIPT, QARI_OCR_BASE_REPO, QARI_OCR_HF_REPO, str(merged_dir)]
        proc = subprocess.Popen(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
            if len(INSTALL_STATE["logs"]) > 20000:
                INSTALL_STATE["logs"] = INSTALL_STATE["logs"][-15000:]
        proc.stdout.close()
        if proc.wait() != 0 or "MERGE_COMPLETE" not in INSTALL_STATE["logs"][-4000:]:
            raise RuntimeError("Failed to merge Qari-OCR LoRA adapter into base model")

        INSTALL_STATE["logs"] += f"\nStep 3/3: Quantizing merged model to native MLX 4-bit (~2.5 GB output)...\n"
        convert_cmd = [
            python_bin, "-m", "mlx_vlm.convert",
            "--hf-path", str(merged_dir),
            "--mlx-path", str(out_dir),
            "-q", "--q-bits", "4"
        ]
        INSTALL_STATE["logs"] += f"Executing: {' '.join(convert_cmd)}\n"
        proc = subprocess.Popen(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        for line in iter(proc.stdout.readline, ''):
            INSTALL_STATE["logs"] += line
            if len(INSTALL_STATE["logs"]) > 20000:
                INSTALL_STATE["logs"] = INSTALL_STATE["logs"][-15000:]
        proc.stdout.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"mlx_vlm.convert exited with code {rc}")

        # Reclaim disk space: the merged fp16 model (~8GB) is no longer needed once quantized.
        INSTALL_STATE["logs"] += "\nCleaning up temporary merged fp16 model to reclaim disk space...\n"
        shutil.rmtree(merged_dir, ignore_errors=True)

        INSTALL_STATE["status"] = "completed"
        INSTALL_STATE["logs"] += f"\n✅ Qari-OCR-0.4.0 MLX model ready at {out_dir}. Starting local MLX-VLM server...\n"
        start_res = _start_mlx_server_process(out_dir)
        INSTALL_STATE["logs"] += f"{start_res['message']}\n"
    except Exception as e:
        shutil.rmtree(merged_dir, ignore_errors=True)
        INSTALL_STATE["status"] = "failed"
        INSTALL_STATE["error"] = str(e)
        INSTALL_STATE["logs"] += f"\n❌ MLX Qari-OCR installation exception: {str(e)}\n"

@router.post("/install-mlx-ocr")
async def install_mlx_ocr(background_tasks: BackgroundTasks):
    """
    Installs mlx & mlx-vlm, downloads NAMAA-Space/Qari-OCR-0.4.0-VL-4B-Instruct, converts it
    to a quantized (4-bit) native MLX model, and starts the local mlx-vlm OpenAI-compatible server.
    Requires an Apple Silicon Mac.
    """
    global INSTALL_STATE
    if not _is_apple_silicon():
        return {"success": False, "message": "MLX requires an Apple Silicon (M-series) Mac."}
    if INSTALL_STATE["status"] == "installing":
        return {"success": False, "message": "An installation is already in progress.", "status": INSTALL_STATE}

    background_tasks.add_task(_run_mlx_ocr_install)
    return {"success": True, "message": "MLX Qari-OCR download & conversion started in background.", "status": INSTALL_STATE}

@router.post("/start-mlx-server")
async def start_mlx_server():
    """Starts (or confirms) the local mlx-vlm OpenAI-compatible server for Qari-OCR."""
    out_dir = _models_dir() / QARI_OCR_MLX_DIRNAME
    if not out_dir.exists():
        return {"success": False, "message": "Qari-OCR MLX model not found. Install it first."}
    return _start_mlx_server_process(out_dir)

@router.post("/start-ollama")
async def start_ollama():
    """
    Attempts to launch Ollama on macOS.
    """
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        # Check if Ollama.app exists in /Applications
        if os.path.exists("/Applications/Ollama.app"):
            subprocess.Popen(["open", "-a", "Ollama"])
            return {"success": True, "message": "Launching Ollama.app..."}
        return {"success": False, "message": "Ollama is not installed. Please download it from https://ollama.ai"}

    try:
        subprocess.Popen([ollama_bin, "serve"])
        await asyncio.sleep(1.5)
        return {"success": True, "message": "Started local Ollama daemon."}
    except Exception as e:
        return {"success": False, "message": f"Failed to start Ollama: {str(e)}"}

@router.post("/pull-ollama-model")
async def pull_ollama_model(req: PullModelRequest):
    """
    Triggers model download in Ollama daemon.
    """
    ollama_url = settings.OLLAMA_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(f"{ollama_url}/api/pull", json={"name": req.model_name, "stream": False})
            if res.status_code == 200:
                return {"success": True, "message": f"Model {req.model_name} pulled successfully."}
            return {"success": False, "message": f"Ollama pull returned status {res.status_code}: {res.text}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to connect to Ollama: {str(e)}"}

@router.get("/arbiter")
async def get_arbiter_engines():
    """
    Returns the real-time Resource Arbiter engine decisions for OCR and Translation.
    100% Local-first, zero cloud transmission.
    """
    from backend.app.providers.arbiter import ResourceArbiter
    return await ResourceArbiter.decide_engines()

class UpdateServersRequest(BaseModel):
    ollama_url: Optional[str] = None
    lmstudio_url: Optional[str] = None
    custom_models_dir: Optional[str] = None

@router.get("/models-hub")
async def get_models_hub_status():
    """
    Comprehensive Local AI Discovery Hub:
    1. Scans the local models folder on disk.
    2. Probes Ollama server connection and lists downloaded models.
    3. Probes LM Studio server connection and lists active models.
    """
    models_dir = _models_dir()

    # 1. Inspect local disk folder
    local_models = []
    total_disk_bytes = 0
    try:
        for item in models_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                total_disk_bytes += size
                local_models.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "folder",
                    "size_mb": round(size / (1024 * 1024), 1),
                    "size_display": f"{round(size / (1024 * 1024 * 1024), 2)} GB" if size > 1024**3 else f"{round(size / (1024 * 1024), 1)} MB",
                    "status": "READY" if (item / "model.bin").exists() or (item / "model.safetensors").exists() or any(item.glob("*.bin")) or any(item.glob("*.safetensors")) else "CONFIGURED"
                })
            elif item.is_file() and (item.suffix in [".gguf", ".bin", ".safetensors", ".pt"]):
                size = item.stat().st_size
                total_disk_bytes += size
                local_models.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "weight_file",
                    "size_mb": round(size / (1024 * 1024), 1),
                    "size_display": f"{round(size / (1024 * 1024 * 1024), 2)} GB" if size > 1024**3 else f"{round(size / (1024 * 1024), 1)} MB",
                    "status": "READY"
                })
    except Exception as e:
        logger.warning(f"Error scanning models directory {models_dir}: {e}")

    # 2. Probe Ollama Server
    ollama_url = settings.OLLAMA_BASE_URL.rstrip("/")
    ollama_connected = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{ollama_url}/api/tags")
            if res.status_code == 200:
                ollama_connected = True
                data = res.json()
                for m in data.get("models", []):
                    m_size = m.get("size", 0)
                    ollama_models.append({
                        "name": m.get("name"),
                        "size_display": f"{round(m_size / (1024 * 1024 * 1024), 2)} GB" if m_size > 0 else "N/A",
                        "modified_at": m.get("modified_at")
                    })
    except Exception:
        pass

    # 3. Probe LM Studio Server
    lmstudio_url = settings.LMSTUDIO_BASE_URL.rstrip("/")
    lmstudio_connected = False
    lmstudio_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{lmstudio_url}/models")
            if res.status_code == 200:
                lmstudio_connected = True
                data = res.json()
                for m in data.get("data", []):
                    lmstudio_models.append({
                        "id": m.get("id"),
                        "object": m.get("object", "model"),
                        "owned_by": m.get("owned_by", "local")
                    })
    except Exception:
        pass

    return {
        "local_folder": {
            "path": str(models_dir),
            "exists": True,
            "total_size_gb": round(total_disk_bytes / (1024**3), 2),
            "models": local_models
        },
        "ollama": {
            "base_url": ollama_url,
            "is_connected": ollama_connected,
            "model_count": len(ollama_models),
            "models": ollama_models
        },
        "lmstudio": {
            "base_url": lmstudio_url,
            "is_connected": lmstudio_connected,
            "model_count": len(lmstudio_models),
            "models": lmstudio_models
        }
    }

@router.post("/models-hub/update-servers")
async def update_servers_config(req: UpdateServersRequest):
    """Updates runtime server URLs for Ollama / LM Studio / MLX-VLM, and optionally relocates the local models folder (e.g. to an external SSD)."""
    if req.ollama_url:
        settings.OLLAMA_BASE_URL = req.ollama_url.strip()
    if req.lmstudio_url:
        settings.LMSTUDIO_BASE_URL = req.lmstudio_url.strip()
    if req.custom_models_dir:
        new_dir = Path(req.custom_models_dir.strip()).expanduser()
        try:
            new_dir.mkdir(parents=True, exist_ok=True)
            # Confirm it's actually writable (e.g. catches unmounted/read-only external drives)
            probe = new_dir / ".tarjuman_write_test"
            probe.write_text("ok")
            probe.unlink()
        except Exception as e:
            return {"success": False, "message": f"Cannot use '{new_dir}': {e}"}

        settings.MODELS_DIR = new_dir
        try:
            import json
            from backend.app.core.config import RUNTIME_CONFIG_PATH
            RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            existing = {}
            if RUNTIME_CONFIG_PATH.exists():
                existing = json.loads(RUNTIME_CONFIG_PATH.read_text())
            existing["models_dir"] = str(new_dir)
            RUNTIME_CONFIG_PATH.write_text(json.dumps(existing, indent=2))
        except Exception as e:
            logger.warning(f"Failed to persist custom models directory: {e}")

    return {"success": True, "message": "Server URLs / models directory updated successfully.", "models_dir": str(settings.MODELS_DIR.resolve())}

@router.post("/models-hub/open-folder")
async def open_models_folder():
    """Opens the local models storage directory in macOS Finder."""
    models_dir = _models_dir()
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(models_dir)])
            return {"success": True, "message": f"Opened {models_dir} in Finder."}
        return {"success": False, "message": f"Directory path: {models_dir}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to open folder: {str(e)}"}


@router.get("/verify-ocr")
async def verify_ocr_server():
    """Health-checks the local Qari-OCR MLX-VLM server."""
    from backend.app.pdf.mlx_ocr_provider import MLXOCRProvider
    status = await MLXOCRProvider.check_availability()
    return {
        "success": status.get("is_available", False),
        "server_url": settings.MLX_VLM_BASE_URL,
        "models": status.get("models", []),
        "message": status.get("status_message", "Unknown")
    }
