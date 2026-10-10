#!/usr/bin/env bash
# Start the QShield Twin backend for local development.
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "error: 'uv' is required (https://docs.astral.sh/uv/)." >&2
  exit 1
fi

# Install/sync dependencies from the lockfile (idempotent).
uv sync

exec uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
