#!/bin/bash
set -e

echo "========================================="
echo "  LeadSite Pro - First Time Setup"
echo "========================================="
echo ""

# Create required directories
echo "[1/5] Creating directories..."
mkdir -p data mockups screenshots exports photos

# Backend setup
echo "[2/5] Setting up Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
echo "[3/5] Installing Python dependencies..."
pip install -r requirements.txt
playwright install chromium
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
