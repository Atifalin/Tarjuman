#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================"
echo "          Tarjuman — Local Translation Workstation      "
echo "        Mac-First • Arabic → Urdu • Real AI Only        "
echo "========================================================"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required. Please install Python 3.10+."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Error: Node.js is required. Please install Node.js 18+."
    exit 1
fi

# Hardware profile check (informational only — the app still runs on any Mac via
# CTranslate2/Argos/Gemini fallbacks, but native MLX OCR requires Apple Silicon).
CHIP_BRAND="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)"
IS_APPLE_SILICON="false"
if [[ "$(uname -m)" == "arm64" ]]; then
    IS_APPLE_SILICON="true"
fi
TOTAL_RAM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))

echo "🖥️  Detected: ${CHIP_BRAND} (${TOTAL_RAM_GB} GB RAM)"
if [[ "$IS_APPLE_SILICON" != "true" ]]; then
    echo "⚠️  Non-Apple-Silicon Mac detected — native MLX OCR (Qari-OCR) will be unavailable."
    echo "    Translation will still work via CTranslate2 / Argos / Gemini."
elif [[ "$TOTAL_RAM_GB" -lt 16 ]]; then
    echo "⚠️  Less than 16GB RAM detected — stick to lightweight models (NLLB-200 1.3B, Qari-OCR 4-bit)."
fi

# Set up virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment in .venv..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install Python requirements if needed
echo "🔍 Checking Python dependencies..."
pip install -q -r backend/requirements.txt

# Install Frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing Frontend npm packages..."
    npm install --prefix frontend
fi

# Create default data directory (models go in data/models unless TARJUMAN_MODELS_DIR
# points elsewhere, e.g. an external SSD: export TARJUMAN_MODELS_DIR=/Volumes/MySSD/tarjuman-models)
mkdir -p data
mkdir -p "${TARJUMAN_MODELS_DIR:-data/models}"
if [ -n "$TARJUMAN_MODELS_DIR" ]; then
    echo "📁 Local models directory: $TARJUMAN_MODELS_DIR"
else
    echo "📁 Local models directory: data/models (set TARJUMAN_MODELS_DIR to use an external drive)"
fi

# Free existing ports if occupied (8082 = local MLX-VLM OCR server)
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5173 | xargs kill -9 2>/dev/null || true
lsof -ti :8082 | xargs kill -9 2>/dev/null || true

echo "🚀 Starting Tarjuman Backend on http://127.0.0.1:8000..."
export PYTHONPATH=.
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

echo "🚀 Starting Tarjuman Frontend on http://127.0.0.1:5173..."
npm run dev --prefix frontend &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "🛑 Shutting down Tarjuman servers..."
    pkill -P $BACKEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    pkill -P $FRONTEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
    lsof -ti :8082 | xargs kill -9 2>/dev/null || true  # local MLX-VLM OCR server (auto-started by backend)
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo ""
echo "========================================================"
echo "✨ Tarjuman is running!"
echo "👉 Frontend Workstation: http://127.0.0.1:5173"
echo "👉 Backend API Docs:     http://127.0.0.1:8000/docs"
echo "--------------------------------------------------------"
echo "First run on this Mac? Open Settings → Setup Wizard and"
echo "click 'Install NLLB-200 1.3B' and 'Install Qari-OCR MLX'"
echo "to download the local translation & Arabic OCR engines."
echo "========================================================"
echo "Press Ctrl+C to stop all servers."

# Open default browser on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2
    open http://127.0.0.1:5173 || true
fi

wait
