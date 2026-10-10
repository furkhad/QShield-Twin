#!/usr/bin/env bash
# Start the QShield Twin frontend dev server.
set -euo pipefail

cd "$(dirname "$0")/../frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "error: 'npm' is required (Node.js 20+)." >&2
  exit 1
fi

# Reproducible install from the lockfile.
npm ci

exec npm run dev
