#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/deploy-server.sh"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "missing script: $SCRIPT_PATH" >&2
  exit 1
fi

HELP_OUTPUT="$(bash "$SCRIPT_PATH" --help)"

grep -Fq -- "/root/zhilian-robot" <<<"$HELP_OUTPUT"
grep -Fq -- "--remove-legacy-copy" <<<"$HELP_OUTPUT"
grep -Fq -- "一键同步本地仓库并在远端部署" <<<"$HELP_OUTPUT"
