#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${1:-${ROOT_DIR}/modules/kag/kag/examples/fact_library/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

HOST_ADDR="${OPENSPG_HOST_ADDR:-http://127.0.0.1:8887}"
COMPOSE_FILE="${ROOT_DIR}/modules/openspg/dev/release/docker-compose.yml"
START_TIMEOUT="${FACT_LIBRARY_OPENSPG_START_TIMEOUT:-3600}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
else
  COMPOSE_CMD=(docker-compose)
fi

"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" up -d
python3 "${ROOT_DIR}/scripts/fact_library/wait_for_http.py" --url "${HOST_ADDR}" --timeout "${START_TIMEOUT}" --interval 5

echo "OpenSPG 已启动: ${HOST_ADDR}"
