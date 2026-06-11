#!/usr/bin/env bash
set -euo pipefail

# MedContradict demo — one-command startup + eval
# Usage: bash scripts/demo_medcontradict.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
API_URL="${API_URL:-http://localhost:8001}"

echo "=== MedContradict Demo ==="
echo ""

# 1. Start infra
echo "1. Starting Qdrant + Ollama..."
docker compose -f "$ROOT_DIR/docker-compose.yml" up qdrant ollama -d 2>/dev/null || true
sleep 3

# 2. Start backend
echo "2. Starting backend..."
cd "$ROOT_DIR"
if ! curl -sf "$API_URL/health" >/dev/null 2>&1; then
    echo "   Backend not running. Starting uvicorn..."
    backend/.venv/bin/python -m uvicorn backend.app.main:app \
        --host 0.0.0.0 --port 8001 &
    BACKEND_PID=$!
    echo "   Waiting for backend (PID=$BACKEND_PID)..."
    for i in $(seq 1 30); do
        if curl -sf "$API_URL/health" >/dev/null 2>&1; then
            echo "   Backend ready."
            break
        fi
        sleep 1
    done
else
    BACKEND_PID=""
    echo "   Backend already running."
fi
echo ""

# 3. Run eval
echo "3. Running MedContradict evaluation..."
echo ""
backend/.venv/bin/python "$SCRIPT_DIR/eval_medcontradict.py" --api-url "$API_URL"
EVAL_EXIT=$?

# 4. Frontend hint
echo ""
echo "=== Frontend ==="
echo "cd frontend && npm run dev"
echo "Open http://localhost:3000/contradictions"
echo ""

# Cleanup
if [ -n "${BACKEND_PID:-}" ]; then
    echo "Stopping backend (PID=$BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
fi

exit $EVAL_EXIT
