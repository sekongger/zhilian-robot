#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/dev/release/docker-compose.yml"
IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG:-openspg-server:local}"
SERVER_URL="${OPENSPG_SERVER_URL:-http://127.0.0.1:8887}"

usage() {
  cat <<EOF
Usage: $0 <command>

Commands:
  build-image   Build local server image with embedded Python+Pemja+KAG runtime
  up            Start full stack (mysql/neo4j/minio/server)
  down          Stop and remove full stack
  restart       Restart server container only
  status        Show compose and container status
  logs          Tail server logs
  verify        Verify health + Python bridge runtime in server container
  all           build-image + up + verify
EOF
}

wait_health() {
  local retries=60
  local i
  for i in $(seq 1 "${retries}"); do
    if curl -fsS "${SERVER_URL}/actuator/health" >/dev/null 2>&1; then
      echo "server health ok: ${SERVER_URL}/actuator/health"
      return 0
    fi
    sleep 3
  done
  echo "server health check timed out"
  return 1
}

verify_runtime() {
  docker exec release-openspg-server sh -lc \
    'PYTHONPATH=/home/admin/miniconda3/lib/python3.10/site-packages /home/admin/miniconda3/bin/python - <<'"'"'PY'"'"'
import os
import kag
import knext
import pemja
from bridge.spg_server_bridge import SPGServerBridge

print("kag=", kag.__file__)
print("knext=", knext.__file__)
print("pemja=", pemja.__file__)
print("bridge=", SPGServerBridge.__name__)
PY'
}

cmd="${1:-}"
if [ -z "${cmd}" ]; then
  usage
  exit 1
fi

case "${cmd}" in
  build-image)
    "${ROOT_DIR}/dev/release/server/build-local-server-image.sh"
    ;;
  up)
    OPENSPG_SERVER_IMAGE="${IMAGE_TAG}" docker compose -f "${COMPOSE_FILE}" up -d
    wait_health
    ;;
  down)
    docker compose -f "${COMPOSE_FILE}" down
    ;;
  restart)
    OPENSPG_SERVER_IMAGE="${IMAGE_TAG}" docker compose -f "${COMPOSE_FILE}" up -d --force-recreate server
    wait_health
    ;;
  status)
    docker compose -f "${COMPOSE_FILE}" ps
    docker ps --filter name=release-openspg --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
    ;;
  logs)
    docker logs -f --tail 200 release-openspg-server
    ;;
  verify)
    wait_health
    verify_runtime
    ;;
  all)
    "${ROOT_DIR}/dev/release/server/build-local-server-image.sh"
    OPENSPG_SERVER_IMAGE="${IMAGE_TAG}" docker compose -f "${COMPOSE_FILE}" up -d
    wait_health
    verify_runtime
    ;;
  *)
    usage
    exit 1
    ;;
esac
