#!/bin/bash
set -e

echo "========================================="
echo "  LeadSite Pro - First Time Setup"
echo "========================================="
echo ""

# Find a compatible Python (3.10-3.13, avoid 3.14 pre-release)
PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$candidate" &>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done

if [ -z "$PYTHON" ]; then
  # Fall back to python3 but warn if it's 3.14+
  PYTHON="python3"
  PY_VERSION=$($PYTHON -c 'import sys; print(sys.version_info.minor)' 2>/dev/null || echo "0")
  if [ "$PY_VERSION" -ge 14 ]; then
    echo "WARNING: Python 3.14+ detected. Many packages lack compiled wheels for pre-release Python."
    echo "Recommended: Install Python 3.12 or 3.13 via 'brew install python@3.12'"
    echo ""
  fi
fi

echo "Using: $PYTHON ($($PYTHON --version 2>&1))"
echo ""

# Install system deps for Pillow (macOS)
if command -v brew &>/dev/null; then
  echo "[0/5] Checking system dependencies..."
  for pkg in jpeg libtiff webp; do
    if ! brew list "$pkg" &>/dev/null; then
      echo "  Installing $pkg via Homebrew..."
      brew install "$pkg"
    fi
  done
  echo ""
fi

# Create required directories
echo "[1/5] Creating directories..."
mkdir -p data mockups screenshots exports photos

# Backend setup
echo "[2/5] Setting up Python virtual environment..."
cd backend
$PYTHON -m venv venv
source venv/bin/activate
echo "[3/5] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# Frontend setup
echo "[4/5] Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Initialize database
echo "[5/5] Initializing database..."
cd backend
source venv/bin/activate
python3 -c "
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from database import init_db
asyncio.run(init_db())
print('Database initialized successfully.')
"
cd ..

echo ""
echo "========================================="
echo "  Setup complete!"
echo "  Run ./start.sh to launch the app"
echo "========================================="
