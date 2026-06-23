#!/usr/bin/env bash
set -euo pipefail

export KAG_PROJECT_HOST_ADDR="${KAG_PROJECT_HOST_ADDR:-${OPENSPG_BASE_URL:-http://172.17.0.1:8887}}"
export KAG_PROJECT_ID="${KAG_PROJECT_ID:-1}"
export KAG_PROJECT_NAMESPACE="${KAG_PROJECT_NAMESPACE:-zhilian}"
export KAG_PROJECT_LANGUAGE="${KAG_PROJECT_LANGUAGE:-zh}"

export KAG_CHAT_API_KEY="${KAG_CHAT_API_KEY:-${OPENAI_API_KEY:-}}"
export KAG_CHAT_API_BASE="${KAG_CHAT_API_BASE:-${OPENAI_API_BASE:-https://api.deepseek.com}}"
export KAG_CHAT_MODEL="${KAG_CHAT_MODEL:-${OPENAI_MODEL:-deepseek-chat}}"

export KAG_VECTOR_API_KEY="${KAG_VECTOR_API_KEY:-${OPENAI_API_KEY:-}}"
export KAG_VECTOR_API_BASE="${KAG_VECTOR_API_BASE:-${OPENAI_API_BASE:-https://api.siliconflow.cn/v1}}"
export KAG_VECTOR_MODEL="${KAG_VECTOR_MODEL:-BAAI/bge-m3}"
export KAG_VECTOR_DIMENSIONS="${KAG_VECTOR_DIMENSIONS:-1024}"

export KAG_MCP_PORT="${KAG_MCP_PORT:-3000}"
export KAG_MCP_TRANSPORT="${KAG_MCP_TRANSPORT:-sse}"
export KAG_MCP_ENABLED_TOOLS="${KAG_MCP_ENABLED_TOOLS:-all}"
export KAG_MCP_LOG_LEVEL="${KAG_MCP_LOG_LEVEL:-INFO}"

if [[ -z "${KAG_CHAT_API_KEY}" ]]; then
  echo "missing KAG_CHAT_API_KEY or OPENAI_API_KEY" >&2
  exit 1
fi

cp /app/deploy/kag-mcp/kag_config.yaml.tmpl /app/runtime/kag_config.yaml
cd /app/runtime

exec kag mcp-server \
  --transport "${KAG_MCP_TRANSPORT}" \
  --port "${KAG_MCP_PORT}" \
  --enabled-tools "${KAG_MCP_ENABLED_TOOLS}"
