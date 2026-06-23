#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_REMOTE_HOST="47.111.125.169"
DEFAULT_REMOTE_USER="root"
DEFAULT_REMOTE_DIR="/root/zhilian-robot"
DEFAULT_LEGACY_DIR="/root/zhilian/zhilian-robot"
DEFAULT_OPENSPG_IMAGE="spg-registry.cn-hangzhou.cr.aliyuncs.com/spg/openspg-server:latest"

REMOTE_HOST="$DEFAULT_REMOTE_HOST"
REMOTE_USER="$DEFAULT_REMOTE_USER"
REMOTE_PORT="22"
REMOTE_DIR="$DEFAULT_REMOTE_DIR"
LEGACY_DIR="$DEFAULT_LEGACY_DIR"
IDENTITY_FILE=""
REMOVE_LEGACY_COPY=0
SKIP_RSYNC=0
SKIP_OPENSPG=0
SKIP_KAG_MCP=0
BUILD_LOCAL_OPENSPG_IMAGE=0
OPENSPG_SERVER_IMAGE_TAG="$DEFAULT_OPENSPG_IMAGE"
OPENSPG_SKIP_MAVEN_BUILD="1"

usage() {
  cat <<EOF
一键同步本地仓库并在远端部署

Usage:
  bash scripts/deploy-server.sh [options]

Options:
  --host <host>                    远端主机，默认: ${DEFAULT_REMOTE_HOST}
  --user <user>                    远端用户，默认: ${DEFAULT_REMOTE_USER}
  --port <port>                    SSH 端口，默认: 22
  --remote-dir <path>              远端唯一部署目录，默认: ${DEFAULT_REMOTE_DIR}
  --identity-file <path>           指定 SSH 私钥
  --remove-legacy-copy             删除旧目录 ${DEFAULT_LEGACY_DIR}
  --legacy-dir <path>              旧目录路径，默认: ${DEFAULT_LEGACY_DIR}
  --skip-rsync                     跳过代码同步，只执行远端部署
  --skip-openspg                   跳过 OpenSPG 栈重启
  --skip-kag-mcp                   跳过 kag-mcp 服务部署
  --build-local-openspg-image      使用远端源码构建 openspg-server:local 再部署
  --openspg-image-tag <tag>        OpenSPG 服务镜像标签
  --skip-maven-build <0|1>         构建本地 OpenSPG 镜像时是否跳过 Maven，默认: 1
  -h, --help                       显示帮助

Examples:
  bash scripts/deploy-server.sh --remove-legacy-copy
  bash scripts/deploy-server.sh --build-local-openspg-image
EOF
}

log() {
  printf '[deploy-server] %s\n' "$1"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command: $1" >&2
    exit 1
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --host)
        REMOTE_HOST="$2"
        shift 2
        ;;
      --user)
        REMOTE_USER="$2"
        shift 2
        ;;
      --port)
        REMOTE_PORT="$2"
        shift 2
        ;;
      --remote-dir)
        REMOTE_DIR="$2"
        shift 2
        ;;
      --identity-file)
        IDENTITY_FILE="$2"
        shift 2
        ;;
      --remove-legacy-copy)
        REMOVE_LEGACY_COPY=1
        shift
        ;;
      --legacy-dir)
        LEGACY_DIR="$2"
        shift 2
        ;;
      --skip-rsync)
        SKIP_RSYNC=1
        shift
        ;;
      --skip-openspg)
        SKIP_OPENSPG=1
        shift
        ;;
      --skip-kag-mcp)
        SKIP_KAG_MCP=1
        shift
        ;;
      --build-local-openspg-image)
        BUILD_LOCAL_OPENSPG_IMAGE=1
        OPENSPG_SERVER_IMAGE_TAG="openspg-server:local"
        shift
        ;;
      --openspg-image-tag)
        OPENSPG_SERVER_IMAGE_TAG="$2"
        shift 2
        ;;
      --skip-maven-build)
        OPENSPG_SKIP_MAVEN_BUILD="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "unknown arg: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

build_ssh_commands() {
  SSH_OPTS=(-p "$REMOTE_PORT" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
  if [[ -n "$IDENTITY_FILE" ]]; then
    SSH_OPTS+=(-i "$IDENTITY_FILE")
  fi

  SSH_BASE=(ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${REMOTE_HOST}")
  RSYNC_SHELL=(ssh "${SSH_OPTS[@]}")
  printf -v RSYNC_RSH '%q ' "${RSYNC_SHELL[@]}"
  RSYNC_RSH="${RSYNC_RSH% }"
}

preflight() {
  need_cmd ssh
  need_cmd rsync

  if [[ -n "$IDENTITY_FILE" && ! -f "$IDENTITY_FILE" ]]; then
    echo "identity file not found: $IDENTITY_FILE" >&2
    exit 1
  fi

  "${SSH_BASE[@]}" "echo connected >/dev/null"
}

sync_repo() {
  if [[ "$SKIP_RSYNC" -eq 1 ]]; then
    log "skip rsync"
    return
  fi

  log "sync repo to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
  "${SSH_BASE[@]}" "mkdir -p '${REMOTE_DIR}'"

  rsync -az --delete \
    --filter='P .env' \
    --filter='P .env.remote' \
    --exclude '.git' \
    --exclude '.github' \
    --exclude '.idea' \
    --exclude '.vscode' \
    --exclude '.worktrees' \
    --exclude '.playwright-cli' \
    --exclude '.pytest_cache' \
    --exclude '__pycache__' \
    --exclude 'node_modules' \
    --exclude '.venv' \
    --exclude 'dist' \
    --exclude 'build' \
    --exclude 'logs' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    --exclude '.env' \
    --exclude '.env.remote' \
    -e "$RSYNC_RSH" \
    "${PROJECT_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"
}

run_remote_deploy() {
  log "run remote deploy"
  "${SSH_BASE[@]}" \
    "REMOTE_DIR='${REMOTE_DIR}' LEGACY_DIR='${LEGACY_DIR}' REMOVE_LEGACY_COPY='${REMOVE_LEGACY_COPY}' SKIP_OPENSPG='${SKIP_OPENSPG}' SKIP_KAG_MCP='${SKIP_KAG_MCP}' BUILD_LOCAL_OPENSPG_IMAGE='${BUILD_LOCAL_OPENSPG_IMAGE}' OPENSPG_SERVER_IMAGE_TAG='${OPENSPG_SERVER_IMAGE_TAG}' OPENSPG_SKIP_MAVEN_BUILD='${OPENSPG_SKIP_MAVEN_BUILD}' bash -s" <<'REMOTE_EOF'
set -euo pipefail

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command on remote host: $1" >&2
    exit 1
  fi
}

ensure_openspg_build_deps() {
  if command -v mvn >/dev/null 2>&1 && [[ -x "${JAVA_HOME:-}/bin/java" ]]; then
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    yum install -y curl tar gzip rsync java-1.8.0-openjdk-devel java-11-openjdk-devel python3 python3-pip maven
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y curl tar gzip rsync java-1.8.0-openjdk-devel java-11-openjdk-devel python3 python3-pip maven
  fi

  if [[ ! -d /opt/apache-maven-3.6.3 ]]; then
    cd /opt
    curl -L --retry 3 --connect-timeout 10 \
      https://repo.huaweicloud.com/apache/maven/maven-3/3.6.3/binaries/apache-maven-3.6.3-bin.tar.gz \
      -o /opt/apache-maven-3.6.3-bin.tar.gz
    tar -xzf /opt/apache-maven-3.6.3-bin.tar.gz
  fi

  export JAVA_HOME=/usr/lib/jvm/java-1.8.0-openjdk
  export PATH=/opt/apache-maven-3.6.3/bin:${JAVA_HOME}/bin:${PATH}
}

need_cmd docker
docker compose version >/dev/null 2>&1

mkdir -p "${REMOTE_DIR}"
cd "${REMOTE_DIR}"

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
fi

if [[ "${REMOVE_LEGACY_COPY}" == "1" && -n "${LEGACY_DIR}" && "${LEGACY_DIR}" != "${REMOTE_DIR}" && -d "${LEGACY_DIR}" ]]; then
  rm -rf "${LEGACY_DIR}"
fi

if [[ "${SKIP_OPENSPG}" != "1" ]]; then
  cd "${REMOTE_DIR}/modules/openspg"

  if [[ "${BUILD_LOCAL_OPENSPG_IMAGE}" == "1" ]]; then
    ensure_openspg_build_deps
    OPENSPG_SERVER_IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG}" \
    OPENSPG_SKIP_MAVEN_BUILD="${OPENSPG_SKIP_MAVEN_BUILD}" \
      ./dev/release/server/build-local-server-image.sh
  fi

  OPENSPG_SERVER_IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG}" ./dev/release/server/deploy-stack.sh up
  curl -fsS "http://127.0.0.1:8887/actuator/health" >/dev/null
fi

cd "${REMOTE_DIR}"
DEPLOY_ARGS=(--skip-pull)
if [[ "${SKIP_KAG_MCP:-0}" == "1" ]]; then
  DEPLOY_ARGS+=(--skip-kag-mcp)
fi
bash deploy.sh "${DEPLOY_ARGS[@]}"
REMOTE_EOF
}

main() {
  parse_args "$@"
  build_ssh_commands
  preflight
  sync_repo
  run_remote_deploy
  log "done: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}"
}

main "$@"
