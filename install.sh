#!/bin/bash
# Tarjuman Bootstrap Installer
# One command to go from a completely clean Mac to a running Tarjuman instance:
#   curl -fsSL <raw-url-to-this-file> | bash
#   -- or, if you already cloned the repo --
#   ./install.sh
#
# Installs (only what's missing, safe to re-run):
#   1. Xcode Command Line Tools (git, clang, etc.)
#   2. Homebrew
#   3. Python 3 & Node.js (via Homebrew)
# Then hands off to run.sh, which creates the venv and installs all app dependencies.
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================"
echo "        Tarjuman — Fresh Mac Bootstrap Installer         "
echo "========================================================"

if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Tarjuman is Mac-only. This installer only supports macOS."
    exit 1
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
    echo "⚠️  Intel Mac detected. Tarjuman will run, but native MLX OCR (Qari-OCR) requires"
    echo "    Apple Silicon (M1 or newer) — translation will still work via CTranslate2/Argos/Gemini."
fi

# ---------------------------------------------------------------
# 1. Xcode Command Line Tools (provides git, clang, make, etc.)
# ---------------------------------------------------------------
if ! xcode-select -p &> /dev/null; then
    echo "📦 Xcode Command Line Tools not found — installing..."
    xcode-select --install &> /dev/null || true
    echo "   A system dialog should have appeared — click 'Install' and accept the license."
    echo "   Waiting for installation to complete (this can take several minutes)..."
    until xcode-select -p &> /dev/null; do
        sleep 5
    done
    echo "✅ Xcode Command Line Tools installed."
else
    echo "✅ Xcode Command Line Tools already installed."
fi

# ---------------------------------------------------------------
# 2. Homebrew
# ---------------------------------------------------------------
if [[ "$ARCH" == "arm64" ]]; then
    BREW_BIN="/opt/homebrew/bin/brew"
else
    BREW_BIN="/usr/local/bin/brew"
fi

if ! command -v brew &> /dev/null && [ ! -x "$BREW_BIN" ]; then
    echo "📦 Homebrew not found — installing (you may be prompted for your password)..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo "✅ Homebrew installed."
else
    echo "✅ Homebrew already installed."
fi

# Make sure brew is on PATH for the rest of this script (fresh installs aren't yet)
if [ -x "$BREW_BIN" ]; then
    eval "$("$BREW_BIN" shellenv)"
fi

if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew installation failed or is not on PATH. Please install it manually: https://brew.sh"
    exit 1
fi

# ---------------------------------------------------------------
# 3. Python 3 & Node.js
# ---------------------------------------------------------------
if ! command -v python3 &> /dev/null; then
    echo "📦 Installing Python 3 via Homebrew..."
    brew install python
else
    echo "✅ Python 3 already installed ($(python3 --version))."
fi

if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js via Homebrew..."
    brew install node
else
    echo "✅ Node.js already installed ($(node --version))."
fi

echo ""
echo "========================================================"
echo "✅ System prerequisites ready. Launching Tarjuman setup..."
echo "========================================================"
echo ""

chmod +x run.sh
exec ./run.sh
