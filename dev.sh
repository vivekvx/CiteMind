#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [ ! -x "$BACKEND_PYTHON" ]; then
  echo "Backend virtualenv not found at backend/.venv."
  echo "Run setup first: cd backend && python3 -m venv .venv && .venv/bin/pip install -r ../requirements.txt"
  exit 1
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "Frontend dependencies not found."
  echo "Run setup first: cd frontend && npm install"
  exit 1
fi

cleanup() {
  echo
  echo "Stopping CiteMind..."
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting CiteMind backend: http://localhost:8001"
(
  cd "$ROOT_DIR"
  "$BACKEND_PYTHON" -m uvicorn backend.app.main:app --reload --port 8001
) &
BACKEND_PID=$!

echo "Starting CiteMind frontend: http://localhost:3001"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --port 3001
) &
FRONTEND_PID=$!

echo
echo "CiteMind is starting."
echo "Open: http://localhost:3001"
echo "Backend docs: http://localhost:8001/docs"
echo "Press Ctrl+C to stop both servers."
echo

wait "$BACKEND_PID" "$FRONTEND_PID"
