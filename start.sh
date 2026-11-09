#!/bin/bash
# Start TKP Generator App on port 3000 (VibeCode default)
set -e

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installing Playwright Chromium..."
playwright install chromium

echo "Starting FastAPI on port 3000..."
exec uvicorn main:app --host 0.0.0.0 --port 3000
