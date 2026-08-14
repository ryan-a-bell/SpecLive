#!/usr/bin/env bash
# Convenience launcher for local development without Docker.
# Runs the API (with SQLite fallback + seed) and the web app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Setting up the API"
cd "$ROOT/apps/api"
python -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -e ".[dev]"
export DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///$ROOT/apps/api/copilot.db}"
alembic upgrade head
python -m app.seed --if-empty
echo "==> Starting API on :8000"
uvicorn app.main:app --reload --port 8000 &
API_PID=$!

echo "==> Setting up the web app"
cd "$ROOT"
npm install --silent
echo "==> Starting web on :3000"
npm run dev --workspace apps/web

kill "$API_PID" 2>/dev/null || true
