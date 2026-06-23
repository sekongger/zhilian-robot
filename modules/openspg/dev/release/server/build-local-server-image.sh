#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
SETTINGS_FILE="${ROOT_DIR}/dev/release/maven/settings-local.xml"
IMAGE_TAG="${OPENSPG_SERVER_IMAGE_TAG:-openspg-server:local}"
JAR_PATH="${ROOT_DIR}/dev/release/server/target/arks-sofaboot-0.0.1-SNAPSHOT-executable.jar"
UI_BASE_IMAGE="${OPENSPG_UI_BASE_IMAGE:-spg-registry.cn-hangzhou.cr.aliyuncs.com/spg/openspg-server:latest}"
KAG_BUNDLE_PATH="${ROOT_DIR}/dev/release/server/target/kag-runtime.tar.gz"
SKIP_MAVEN_BUILD="${OPENSPG_SKIP_MAVEN_BUILD:-0}"

if ! command -v mvn >/dev/null 2>&1; then
  echo "mvn command not found"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command not found"
  exit 1
fi

if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  if [ -x /usr/libexec/java_home ]; then
    JAVA_HOME="$(/usr/libexec/java_home -v 1.8 2>/dev/null || true)"
  fi
fi

if [ -z "${JAVA_HOME:-}" ] || [ ! -x "${JAVA_HOME}/bin/java" ]; then
  echo "JDK8 not found, please set JAVA_HOME to a Java 8 installation"
  exit 1
fi

export JAVA_HOME
export PATH="${JAVA_HOME}/bin:${PATH}"
export MAVEN_SKIP_RC=1

ensure_ui_assets_in_jar() {
  if [ ! -f "${JAR_PATH}" ]; then
    echo "server jar not found: ${JAR_PATH}"
    exit 1
  fi

  if jar tf "${JAR_PATH}" | grep -q '^BOOT-INF/classes/static/index.html$'; then
    echo "ui assets already present in local jar"
    return 0
  fi

  echo "ui assets missing in local jar, importing from ${UI_BASE_IMAGE}"
  local tmp_dir
  local donor_jar
  local donor_extract_dir
  local donor_container
  tmp_dir="$(mktemp -d)"
  donor_jar="${tmp_dir}/official-arks-sofaboot.jar"
  donor_extract_dir="${tmp_dir}/official-extract"
  donor_container="$(docker create "${UI_BASE_IMAGE}")"

  docker cp "${donor_container}:/arks-sofaboot-0.0.1-SNAPSHOT-executable.jar" "${donor_jar}"
  docker rm "${donor_container}" >/dev/null
  mkdir -p "${donor_extract_dir}"
  (
    cd "${donor_extract_dir}"
    jar xf "${donor_jar}" BOOT-INF/classes/static
  )

  if [ ! -f "${donor_extract_dir}/BOOT-INF/classes/static/index.html" ]; then
    echo "official image has no static/index.html: ${UI_BASE_IMAGE}"
    rm -rf "${tmp_dir}"
    exit 1
  fi

  (
    cd "${donor_extract_dir}"
    jar uf "${JAR_PATH}" BOOT-INF/classes/static
  )

  rm -rf "${tmp_dir}"

  if ! jar tf "${JAR_PATH}" | grep -q '^BOOT-INF/classes/static/index.html$'; then
    echo "injecting ui assets failed for ${JAR_PATH}"
    exit 1
  fi

  echo "ui assets injected into local jar"
}

prepare_server_jar_from_base_image() {
  local donor_container
  mkdir -p "$(dirname "${JAR_PATH}")"
  donor_container="$(docker create "${UI_BASE_IMAGE}")"
  docker cp "${donor_container}:/arks-sofaboot-0.0.1-SNAPSHOT-executable.jar" "${JAR_PATH}"
  docker rm "${donor_container}" >/dev/null
  if [ ! -s "${JAR_PATH}" ]; then
    echo "failed to copy server jar from ${UI_BASE_IMAGE}"
    exit 1
  fi
  echo "server jar copied from base image: ${UI_BASE_IMAGE}"
}

resolve_kag_root() {
  local candidate
  for candidate in "${ROOT_DIR}/KAG" "${ROOT_DIR}/../kag"; do
    if [ -d "${candidate}/kag" ] && [ -d "${candidate}/knext" ]; then
      echo "${candidate}"
      return 0
    fi
  done

  return 1
}

prepare_kag_runtime_bundle() {
  local kag_root
  kag_root="$(resolve_kag_root || true)"
  if [ ! -d "${kag_root}/kag" ] || [ ! -d "${kag_root}/knext" ]; then
    echo "KAG source not found under ${ROOT_DIR}/KAG or ${ROOT_DIR}/../kag"
    exit 1
  fi

  mkdir -p "$(dirname "${KAG_BUNDLE_PATH}")"
  rm -f "${KAG_BUNDLE_PATH}"

  tar -czf "${KAG_BUNDLE_PATH}" \
    --exclude='kag/open_benchmark' \
    --exclude='kag/examples' \
    --exclude='kag/tests' \
    --exclude='kag/.pytest_cache' \
    -C "${kag_root}" \
    kag knext

  if [ ! -s "${KAG_BUNDLE_PATH}" ]; then
    echo "failed to prepare KAG runtime bundle: ${KAG_BUNDLE_PATH}"
    exit 1
  fi
  echo "kag runtime bundle prepared: ${KAG_BUNDLE_PATH}"
}

if [ "${SKIP_MAVEN_BUILD}" = "1" ]; then
  echo "[1/4] skip maven build, reuse server jar from ${UI_BASE_IMAGE}"
  prepare_server_jar_from_base_image
else
  echo "[1/4] build server executable jar with local maven settings"
  mvn -s "${SETTINGS_FILE}" \
    -pl server/arks/sofaboot \
    -am package \
    -Dmaven.test.skip=true \
    -DskipTests \
    -DskipITs \
    -Dspotless.check.skip=true \
    -Dspotless.skip=true
fi

echo "[2/4] ensure OpenSPG console static assets exist"
ensure_ui_assets_in_jar

echo "[3/4] prepare KAG runtime bundle"
prepare_kag_runtime_bundle

echo "[4/4] build docker image: ${IMAGE_TAG}"
docker build -f "${ROOT_DIR}/dev/release/server/Dockerfile" \
  -t "${IMAGE_TAG}" \
  "${ROOT_DIR}/dev/release/server"

echo "done: ${IMAGE_TAG}"
