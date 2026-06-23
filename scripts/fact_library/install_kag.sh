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

VENV_DIR="${FACT_LIBRARY_VENV_DIR:-${ROOT_DIR}/.venv-kag}"
INSTALL_MODE="${FACT_LIBRARY_KAG_INSTALL_MODE:-minimal}"

get_python_minor_version() {
  "$1" - <<'PY'
import sys
print(f"{sys.version_info[0]}.{sys.version_info[1]}")
PY
}

choose_python_bin() {
  local requested="${FACT_LIBRARY_PYTHON_BIN:-}"
  local candidate=""
  local version=""

  if [[ -n "${requested}" ]]; then
    if command -v "${requested}" >/dev/null 2>&1; then
      echo "${requested}"
      return 0
    fi
    echo "Python not found: ${requested}" >&2
    exit 1
  fi

  for candidate in python3 /usr/bin/python3; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      version="$(get_python_minor_version "${candidate}")"
      if [[ "${version}" != "3.13" && "${version}" != "3.14" && "${version}" != "3.15" ]]; then
        echo "${candidate}"
        return 0
      fi
    fi
  done

  echo "python3"
}

PYTHON_BIN="$(choose_python_bin)"
TARGET_PYTHON_VERSION="$(get_python_minor_version "${PYTHON_BIN}")"

"${PYTHON_BIN}" - <<'PY'
import sys
major, minor = sys.version_info[:2]
if (major, minor) >= (3, 13):
    print("WARN: 当前 Python 版本 >= 3.13，KAG 官方更常见的是 3.10/3.11。若安装失败，请改用 FACT_LIBRARY_PYTHON_BIN 指向 3.10/3.11。")
PY

if [[ -x "${VENV_DIR}/bin/python" ]]; then
  CURRENT_VENV_VERSION="$("${VENV_DIR}/bin/python" - <<'PY'
import sys
print(f"{sys.version_info[0]}.{sys.version_info[1]}")
PY
)"
  if [[ "${CURRENT_VENV_VERSION}" != "${TARGET_PYTHON_VERSION}" ]]; then
    rm -rf "${VENV_DIR}"
  fi
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

if [[ "${INSTALL_MODE}" == "full" ]]; then
  "${VENV_DIR}/bin/pip" install -e "${ROOT_DIR}/modules/kag"
else
  "${VENV_DIR}/bin/pip" install \
    wget==3.2 \
    pytest==7.4.2 \
    click \
    requests \
    urllib3==1.26.16 \
    certifi \
    charset_normalizer==3.3.2 \
    ruamel.yaml \
    PyYAML \
    Jinja2 \
    retrying==1.3.4 \
    tenacity \
    json5 \
    jieba==0.42.1 \
    nltk==3.8.1 \
    pandas \
    numpy \
    networkx==3.1 \
    psutil \
    tqdm==4.66.1 \
    tabulate==0.9.0 \
    pydantic \
    python-dateutil==2.8.2 \
    dateutils==0.6.12 \
    cachetools==5.3.2 \
    six==1.16.0 \
    protobuf==3.20.1 \
    neo4j \
    openai \
    ollama \
    dashscope \
    pycryptodome \
    pypdf \
    PyPDF2 \
    pdfminer.six==20231228 \
    python-docx \
    markdown==3.7 \
    bs4 \
    gitpython \
    json_repair \
    pyhocon \
    docstring_parser \
    aiolimiter \
    schedule \
    zodb \
    matplotlib \
    aiofiles \
    httpx \
    diskcache \
    portalocker \
    deprecated
  "${VENV_DIR}/bin/pip" install --no-deps -e "${ROOT_DIR}/modules/kag"
fi

echo "KAG 安装完成: ${VENV_DIR} (mode=${INSTALL_MODE}, python=${PYTHON_BIN}, version=${TARGET_PYTHON_VERSION})"
