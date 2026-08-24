# Tarjuman (ترجمان)
### Mac-First • Local-First • Cloud-Optional • Real AI Only
**Local Arabic → Urdu Document Translation Workstation for Apple Silicon Macs**

Tarjuman is a local, privacy-first translation workstation engineered for Apple Silicon Macs (M1/M2/M3/M4) with 16 GB and 32 GB unified memory. It processes large Arabic PDF libraries with page preservation, intelligent punctuation-aware chunking, side-by-side human review in Nastaliq script, automated deterministic QA, and crash-resilient SQLite state tracking.

---

## 🌟 Key Features

1. **Local-First AI Engine Orchestration**:
   - **Ollama**: Connects to `http://127.0.0.1:11434` for local models like `qwen2.5:7b` / `14b`.
   - **LM Studio**: Connects to `http://127.0.0.1:1234/v1` OpenAI-compatible local servers.
   - **Direct PyTorch / Transformers / CTranslate2**: Dedicated Seq2Seq Machine Translation engines — **Meta NLLB-200 1.3B Distilled** (default, CTranslate2 int8, direct `ar → ur`) and Google MADLAD-400 7B MT.
   - **Native MLX (Apple Silicon GPU)**: **Qari-OCR-0.4.0** (Qwen3-VL-4B fine-tune) for Arabic manuscript/book OCR, served locally via `mlx-vlm`'s OpenAI-compatible server — zero cloud, no Ollama dependency.
   - **Real Google Gemini API (Cloud Optional)**: Optional cloud translator and deep reviewer (`gemini-2.5-flash`, `gemini-2.5-pro`) with clear privacy indicators (`⚠ CLOUD AI ENABLED`), macOS Keychain credential security, and daily quota/token estimation trackers.
   - **Zero Fake/Mock Output**: Workstation strictly requires verified real AI providers.

2. **Apple Silicon Hardware & Memory Safety Guard**:
   - Live telemetry monitoring chip model, unified RAM used/total, CPU %, and memory pressure (`GREEN`, `YELLOW`, `RED`).
   - Dynamic memory throttling: automatically adapts between **16 GB Compatibility Profile** (conservative 1-model lifecycle) and **32 GB Performance Profile** (high throughput).

3. **Desktop-Class Human Review Workstation**:
   - Side-by-side bidirectional view: Arabic Source (Amiri typography) vs Urdu Translation (Noto Nastaliq Urdu typography).
   - Real-time model provenance banner (`Primary: MADLAD-400 | Reviewer: Qwen2.5 | Latency: 380ms`).
   - Deterministic QA Drawer: flags dropped numerals, conversational fluff, and length anomalies without fake confidence percentages.
   - Keyboard shortcuts: `Enter` (Approve), `R` (Regenerate), `G` (Gemini Review), `X` (Reject), `E` (Edit).

4. **Multi-Document Batching & Crash Resilience**:
   - Scans folders for Arabic PDFs, extracts text with layout preservation, and detects scanned pages.
   - Persists state atomically per chunk in SQLite with Write-Ahead Logging (`WAL`).
   - Resume anytime after Mac restart or app close.

5. **Terminology & Translation Memory**:
   - Persistent glossary management with category filtering and CSV import/export.
   - Exact-match Translation Memory indexing with SHA-256 hashes.

6. **Built-in 10-Category Arabic Benchmark Suite**:
   - Benchmark models against Classical Arabic, Hadith/Quranic terminology, academic text, numbers/dates, and difficult idioms with manual human ranking (1–5 stars).

7. **Multi-Format Document Exporter**:
   - Export translated projects to formatted Microsoft Word (`.docx`) with proper Urdu RTL paragraph direction and page markers, bilingual `.txt`, and structured `.json`.

---

## 🚀 Quick Start

### Requirements
- Any Apple Silicon Mac (M1 or newer; **M2+ with 16GB+ RAM recommended** for the local Qari-OCR/NLLB engines) — Intel Macs work too via CTranslate2/Argos/Gemini, minus native MLX OCR.

### 1a. Completely fresh Mac (no Xcode, Homebrew, Python, or Node installed)
```bash
git clone <this-repo-url> Tarjuman
cd Tarjuman
./install.sh
```
`install.sh` installs Xcode Command Line Tools, Homebrew, Python 3, and Node.js (skipping anything already present), then hands off to `run.sh` automatically. One command, no manual steps.

### 1b. Already have Python 3 & Node.js
```bash
./run.sh
```
This script will:
1. Initialize the Python virtual environment and install dependencies.
2. Install frontend packages.
3. Start the FastAPI backend on `http://127.0.0.1:8000`.
4. Start the Vite React frontend on `http://127.0.0.1:5173`.
5. Automatically open the workstation in your browser.

### 2. Install the local AI engines
On first run, open **Settings → Setup Wizard** in the app and click:
- **Install NLLB-200 1.3B** — downloads & converts Meta's translation model to CTranslate2 int8 (~2.6 GB).
- **Install Qari-OCR MLX** — downloads the Qwen3-VL-4B base model + Qari-OCR LoRA adapter, merges and quantizes them to native MLX 4-bit (~2.5 GB final size; requires Apple Silicon).

Both run as background jobs with live progress logs and persist across restarts.

### Using an external drive for model storage
If your internal disk is low on space, open **Settings → AI Engines & Model Discovery Hub** and enter a path (e.g. `/Volumes/MySSD/tarjuman-models`) in the **Local Model Weights Folder** field, then click **Use This Folder**. This is saved permanently and applies to all future downloads. You can also set it via an environment variable before launching:
```bash
TARJUMAN_MODELS_DIR=/Volumes/MySSD/tarjuman-models ./run.sh
```

---

## 🧪 Running Automated Tests

Run the backend test suite:
```bash
source .venv/bin/activate
PYTHONPATH=. pytest backend/tests -v
```

---

## 🔒 Privacy Guarantee
By default, Tarjuman operates in `✓ LOCAL ONLY` mode. No document text leaves your Mac unless you explicitly configure a Gemini API key and select a cloud routing mode.
