#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

mkdir -p "$ROOT/logs" "$ROOT/data" "$ROOT/data/uploads"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

export APP_HOST="${APP_HOST:-0.0.0.0}"
export APP_PORT="${APP_PORT:-8001}"

PY=python3.8
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

if ! "$PY" -c "import requests" 2>/dev/null; then
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
fi

echo "Starting on ${APP_HOST}:${APP_PORT} ..."
exec "$PY" -u app.py
