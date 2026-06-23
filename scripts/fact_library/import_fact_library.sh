#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/modules/kag/kag/examples/fact_library/.env"
DATASET=""
WITH_TEXT=0
START_OPENSPG=1
INSTALL_KAG=1
COMMIT_SCHEMA=1
IMPORT_STRUCTURED=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --dataset)
      DATASET="$2"
      shift 2
      ;;
    --with-text)
      WITH_TEXT=1
      shift
      ;;
    --skip-start-openspg)
      START_OPENSPG=0
      shift
      ;;
    --skip-install-kag)
      INSTALL_KAG=0
      shift
      ;;
    --skip-schema)
      COMMIT_SCHEMA=0
      shift
      ;;
    --skip-structured)
      IMPORT_STRUCTURED=0
      shift
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

if [[ -z "${DATASET}" ]]; then
  DATASET="${FACT_LIBRARY_DATASET:-20260313_183538}"
fi

if [[ "${START_OPENSPG}" -eq 1 ]]; then
  bash "${ROOT_DIR}/scripts/fact_library/start_openspg_stack.sh" "${ENV_FILE}"
fi

if [[ "${INSTALL_KAG}" -eq 1 ]]; then
  bash "${ROOT_DIR}/scripts/fact_library/install_kag.sh" "${ENV_FILE}"
fi

VENV_DIR="${FACT_LIBRARY_VENV_DIR:-${ROOT_DIR}/.venv-kag}"
PYTHON_BIN="${VENV_DIR}/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python venv not found: ${PYTHON_BIN}" >&2
  exit 1
fi

"${PYTHON_BIN}" "${ROOT_DIR}/scripts/fact_library/render_fact_library_kag_config.py" --env-file "${ENV_FILE}"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/fact_library/render_fact_library_schema.py" --env-file "${ENV_FILE}"
"${PYTHON_BIN}" "${ROOT_DIR}/scripts/fact_library/ensure_openspg_project.py" --env-file "${ENV_FILE}"

pushd "${ROOT_DIR}/modules/kag/kag/examples/fact_library" >/dev/null

if [[ "${COMMIT_SCHEMA}" -eq 1 ]]; then
  "${PYTHON_BIN}" -m knext.command.knext_cli schema commit
fi

if [[ "${IMPORT_STRUCTURED}" -eq 1 ]]; then
  "${PYTHON_BIN}" builder/indexer.py --dataset "${DATASET}"
fi

if [[ "${WITH_TEXT}" -eq 1 ]]; then
  "${PYTHON_BIN}" builder/indexer.py --dataset "${DATASET}" --with-text
fi

popd >/dev/null

echo "事实库导入完成: dataset=${DATASET}, with_text=${WITH_TEXT}"
