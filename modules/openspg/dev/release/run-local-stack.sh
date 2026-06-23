#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
export OPENSPG_SERVER_IMAGE="${OPENSPG_SERVER_IMAGE:-openspg-server:local}"

docker compose -f "${ROOT_DIR}/dev/release/docker-compose.yml" up -d
echo "stack started with OPENSPG_SERVER_IMAGE=${OPENSPG_SERVER_IMAGE}"
