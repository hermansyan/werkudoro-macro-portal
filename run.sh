#!/bin/bash
set -e
PORT=8000
HOST="0.0.0.0"

echo "Starting Werkudoro Macroeconomic Intelligence Portal on http://${HOST}:${PORT}..."
cd /home/hermes/macro-portal
export PYTHONPATH=/home/hermes/macro-portal
exec /home/hermes/macro-env/bin/python3 -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" --workers 1
