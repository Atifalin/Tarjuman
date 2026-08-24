# Tarjuman (ترجمان)
### Mac-First • Local-First • Cloud-Optional • Real AI Only
**Local Arabic → Urdu Document Translation Workstation for Apple Silicon Macs**

Tarjuman is a local, privacy-first translation workstation engineered for Apple Silicon Macs (M1/M2/M3/M4) with 16 GB and 32 GB unified memory. It processes large Arabic PDF libraries with page preservation, intelligent punctuation-aware chunking, side-by-side human review in Nastaliq script, automated deterministic QA, and crash-resilient SQLite state tracking.

---

## 🌟 Key Features

1. **Local-First AI Engine Orchestration**:
   - **Ollama**: Connects to `http://127.0.0.1:11434` for local models like `qwen2.5:7b` / `14b`.
   - **LM Studio**: Connects to `http://127.0.0.1:1234/v1` OpenAI-compatible local servers.
   - **Direct PyTorch / Transformers / MLX**: Dedicated Seq2Seq Machine Translation engines (Google MADLAD-400 7B MT, Meta NLLB-200 3.3B).
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

### 1. Launch the Workstation
Run the single launcher script:
```bash
./run.sh
```
This script will:
1. Initialize the Python virtual environment and install dependencies.
2. Install frontend packages.
3. Start the FastAPI backend on `http://127.0.0.1:8000`.
4. Start the Vite React frontend on `http://127.0.0.1:5173`.
5. Automatically open the workstation in your browser.

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
