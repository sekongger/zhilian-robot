#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sync_and_remote_deploy.sh \
    --host <REMOTE_HOST> \
    --password <REMOTE_PASSWORD> \
    [--user root] \
    [--remote-root /root/zhilian] \
    [--openspg-base-url http://172.17.0.1:8887] \
    [--image-tag openspg-server:local] \
    [--skip-maven-build 1]

Example:
  ./scripts/sync_and_remote_deploy.sh \
    --host 47.111.125.169 \
    --password 'your_password'
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing command: $1"
    exit 1
  fi
}

REMOTE_HOST=""
REMOTE_USER="root"
REMOTE_PASSWORD=""
REMOTE_ROOT="/root/zhilian"
OPENSPG_BASE_URL="http://172.17.0.1:8887"
OPENSPG_SERVER_IMAGE_TAG="openspg-server:local"
OPENSPG_SKIP_MAVEN_BUILD="1"

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
    --password)
      REMOTE_PASSWORD="$2"
      shift 2
      ;;
    --remote-root)
      REMOTE_ROOT="$2"
      shift 2
      ;;
    --openspg-base-url)
      OPENSPG_BASE_URL="$2"
      shift 2
      ;;
    --image-tag)
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
      echo "unknown arg: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${REMOTE_HOST}" || -z "${REMOTE_PASSWORD}" ]]; then
  usage
  exit 1
fi

need_cmd sshpass
need_cmd ssh
need_cmd rsync

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENSPG_DIR="${ROOT_DIR}"
ZHILIAN_DIR="${ROOT_DIR}/zhilian-robot"

if [[ ! -d "${ZHILIAN_DIR}" ]]; then
  echo "zhilian-robot not found: ${ZHILIAN_DIR}"
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)
SSH_BASE=(sshpass -p "${REMOTE_PASSWORD}" ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${REMOTE_HOST}")

echo "[1/6] prepare remote directories"
"${SSH_BASE[@]}" "mkdir -p '${REMOTE_ROOT}/openspg' '${REMOTE_ROOT}/zhilian-robot'"

echo "[2/6] sync openspg source to ${REMOTE_ROOT}/openspg"
rsync -az --delete \
  --exclude ".git" \
  --exclude ".idea" \
  --exclude ".vscode" \
  --exclude "node_modules" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  --exclude "target" \
  --exclude "logs" \
  --exclude "*.log" \
  -e "sshpass -p '${REMOTE_PASSWORD}' ssh ${SSH_OPTS[*]}" \
  "${OPENSPG_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ROOT}/openspg/"

echo "[3/6] sync zhilian-robot source to ${REMOTE_ROOT}/zhilian-robot"
rsync -az --delete \
  --exclude ".git" \
  --exclude ".idea" \
  --exclude ".vscode" \
  --exclude "node_modules" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".pytest_cache" \
  --exclude "dist" \
  --exclude "build" \
  --exclude "logs" \
  --exclude "*.log" \
  -e "sshpass -p '${REMOTE_PASSWORD}' ssh ${SSH_OPTS[*]}" \
  "${ZHILIAN_DIR}/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_ROOT}/zhilian-robot/"

echo "[4/6] install remote dependencies and build openspg local image"
"${SSH_BASE[@]}" \
  "REMOTE_ROOT='${REMOTE_ROOT}' OPENSPG_SERVER_IMAGE_TAG='${OPENSPG_SERVER_IMAGE_TAG}' OPENSPG_SKIP_MAVEN_BUILD='${OPENSPG_SKIP_MAVEN_BUILD}' bash -s" <<'REMOTE_EOF'
set -euo pipefail

if command -v yum >/dev/null 2>&1; then
  yum install -y curl tar gzip rsync java-1.8.0-openjdk-devel java-11-openjdk-devel python3 python3-pip maven
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y curl tar gzip rsync java-1.8.0-openjdk-devel java-11-openjdk-devel python3 python3-pip maven
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found on remote host"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin not found on remote host"
  exit 1
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

cd "${REMOTE_ROOT}/openspg"
OPENSPG_SERVER_IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG}" OPENSPG_SKIP_MAVEN_BUILD="${OPENSPG_SKIP_MAVEN_BUILD}" ./dev/release/server/build-local-server-image.sh
REMOTE_EOF

echo "[5/6] start openspg stack and verify runtime"
"${SSH_BASE[@]}" \
  "REMOTE_ROOT='${REMOTE_ROOT}' OPENSPG_SERVER_IMAGE_TAG='${OPENSPG_SERVER_IMAGE_TAG}' bash -s" <<'REMOTE_EOF'
set -euo pipefail
cd "${REMOTE_ROOT}/openspg"
OPENSPG_SERVER_IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG}" ./dev/release/server/deploy-stack.sh up
OPENSPG_SERVER_IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG}" ./dev/release/server/deploy-stack.sh verify
REMOTE_EOF

echo "[6/6] start zhilian-robot stack and run health checks"
"${SSH_BASE[@]}" \
  "REMOTE_ROOT='${REMOTE_ROOT}' OPENSPG_BASE_URL='${OPENSPG_BASE_URL}' bash -s" <<'REMOTE_EOF'
set -euo pipefail
ENV_FILE="${REMOTE_ROOT}/zhilian-robot/.env"
EXAMPLE_FILE="${REMOTE_ROOT}/zhilian-robot/.env.example"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${EXAMPLE_FILE}" "${ENV_FILE}"
fi

upsert_env() {
  local key="$1"
  local value="$2"
  local tmp_file
  tmp_file="$(mktemp)"
  grep -v "^${key}=" "${ENV_FILE}" > "${tmp_file}" || true
  printf "%s=%s\n" "${key}" "${value}" >> "${tmp_file}"
  mv "${tmp_file}" "${ENV_FILE}"
}

upsert_env "OPENSPG_BASE_URL" "${OPENSPG_BASE_URL}"
upsert_env "MYSQL_PORT" "3307"

cd "${REMOTE_ROOT}/zhilian-robot"
docker compose down || true
docker compose up -d --build

BACKEND_PORT="$(grep '^BACKEND_PORT=' "${ENV_FILE}" | tail -n1 | cut -d= -f2)"
FRONTEND_PORT="$(grep '^FRONTEND_PORT=' "${ENV_FILE}" | tail -n1 | cut -d= -f2)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8100}"

curl -fsS "http://127.0.0.1:8887/actuator/health" >/dev/null
curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null

echo "OpenSPG: http://$(hostname -I | awk '{print $1}'):8887"
echo "Zhilian frontend: http://$(hostname -I | awk '{print $1}'):${FRONTEND_PORT}"
echo "Zhilian backend: http://$(hostname -I | awk '{print $1}'):${BACKEND_PORT}"
REMOTE_EOF

echo "deploy completed: ${REMOTE_HOST}"
