#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ENV_FILE="$ROOT_DIR/.env.remote"
COMPOSE=(docker compose)
FULL_SERVICES=(backend frontend celery-worker celery-beat flower)

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  echo "请先创建 .env.remote 后再执行。"
  exit 1
fi

cmd="${1:-up}"
shift || true

case "$cmd" in
  up)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --no-deps backend frontend "$@"
    ;;
  full-up)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --no-deps "${FULL_SERVICES[@]}" "$@"
    ;;
  down)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" down "$@"
    ;;
  restart)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --no-deps --force-recreate backend frontend "$@"
    ;;
  full-restart)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" up -d --no-deps --force-recreate "${FULL_SERVICES[@]}" "$@"
    ;;
  logs)
    "${COMPOSE[@]}" --env-file "$ENV_FILE" logs -f --tail=200 backend frontend "$@"
    ;;
  *)
    echo "Usage: $0 [up|full-up|down|restart|full-restart|logs] [compose-args...]"
    exit 1
    ;;
 esac
