#!/usr/bin/env bash
# Build the production images locally.
#
# Produces exactly the image names/tags the published stack uses, so that
# `docker-compose.prod.yml` works identically before and after GHCR publishing:
#
#   ghcr.io/furkhad/qshield-twin-backend:<tag>
#   ghcr.io/furkhad/qshield-twin-frontend:<tag>
#
# Usage:
#   scripts/build-prod-images.sh [tag]      # default tag: local
#
# This is the "safe way to test images locally before GHCR publishing exists":
# nothing is pushed, and the same Compose file is used for local and published
# images.
set -euo pipefail

cd "$(dirname "$0")/.."

TAG="${1:-local}"
BACKEND_IMAGE="ghcr.io/furkhad/qshield-twin-backend:${TAG}"
FRONTEND_IMAGE="ghcr.io/furkhad/qshield-twin-frontend:${TAG}"

if ! command -v docker >/dev/null 2>&1; then
  echo "error: 'docker' is required." >&2
  exit 1
fi

echo "Building ${BACKEND_IMAGE}"
docker build -f backend/Dockerfile -t "${BACKEND_IMAGE}" .

echo "Building ${FRONTEND_IMAGE}"
docker build -f frontend/Dockerfile.prod -t "${FRONTEND_IMAGE}" ./frontend

cat <<EOF

Built:
  ${BACKEND_IMAGE}
  ${FRONTEND_IMAGE}

Run the production stack with:
  cp .env.production.example .env.production   # then fill in the secrets
  QSHIELD_IMAGE_TAG=${TAG} docker compose -f docker-compose.prod.yml --env-file .env.production up -d

Nothing was pushed to a registry.
EOF
