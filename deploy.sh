#!/usr/bin/env bash

###############################################################################
# 智链机器人 - 通用部署脚本
# 用途: 可选拉代码 + 基于指定 env 文件重建并启动服务
# 示例:
#   bash deploy.sh
#   bash deploy.sh --env-file .env.remote --skip-pull
#   bash deploy.sh --env-file .env.remote --skip-pull --skip-build
###############################################################################

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SKIP_PULL=0
SKIP_BUILD=0
SKIP_DOWN=0
SKIP_KAG_MCP=0

if [[ "$(uname)" == "Darwin" ]]; then
    ENV_TYPE="local"
    get_ip() { ipconfig getifaddr en0 2>/dev/null || echo "localhost"; }
else
    ENV_TYPE="server"
    get_ip() { hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"; }
fi

usage() {
    cat <<EOF
Usage: bash deploy.sh [options]

Options:
  --env-file <path>   指定环境变量文件（默认: .env）
  --skip-pull         跳过 git pull
  --skip-build        跳过 backend/frontend build
  --skip-down         跳过 docker compose down
  --skip-kag-mcp      跳过启动 kag-mcp 服务
  -h, --help          显示帮助
EOF
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_separator() { echo "=============================================================================="; }

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "未检测到命令: $1"
        exit 1
    fi
}

get_env_value() {
    local key="$1"
    local default_value="${2:-}"
    local value
    value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
    if [[ -n "$value" ]]; then
        echo "$value"
    elif [[ -n "${!key:-}" ]]; then
        echo "${!key}"
    else
        echo "$default_value"
    fi
}

wait_http() {
    local url="$1"
    local label="$2"
    local retries="${3:-20}"
    local sleep_seconds="${4:-3}"
    local i

    if ! command -v curl >/dev/null 2>&1; then
        log_warning "未检测到 curl，跳过 ${label} 检查: ${url}"
        return 0
    fi

    for ((i=1; i<=retries; i++)); do
        if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
            log_success "${label} 可用: ${url}"
            return 0
        fi
        sleep "$sleep_seconds"
    done

    log_warning "${label} 在超时内未就绪: ${url}"
    return 1
}

service_is_running() {
    local service_name="$1"
    local output
    output="$("${COMPOSE[@]}" ps "$service_name" 2>/dev/null || true)"
    [[ "$output" == *" Up "* ]]
}

ensure_frontend_running() {
    if service_is_running "frontend"; then
        return 0
    fi

    log_warning "frontend 未自动拉起，尝试单独启动 frontend"
    "${COMPOSE[@]}" up -d frontend
}

check_openspg() {
    local base_url="$1"
    local normalized="${base_url%/}"
    local endpoints=("/actuator/health" "/api/v1/project/list" "/")
    local path

    if ! command -v curl >/dev/null 2>&1; then
        log_warning "未检测到 curl，跳过 OpenSPG 可达性检查"
        return 0
    fi

    for path in "${endpoints[@]}"; do
        if curl -fsS --max-time 5 "${normalized}${path}" >/dev/null 2>&1; then
            log_success "OpenSPG 可达: ${normalized}${path}"
            return 0
        fi
    done

    log_warning "OpenSPG 检查失败，请确认 OPENSPG_BASE_URL 是否正确: ${normalized}"
    return 1
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            --skip-pull)
                SKIP_PULL=1
                shift
                ;;
            --skip-build)
                SKIP_BUILD=1
                shift
                ;;
            --skip-down)
                SKIP_DOWN=1
                shift
                ;;
            --skip-kag-mcp)
                SKIP_KAG_MCP=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [[ "$ENV_FILE" != /* ]]; then
        ENV_FILE="$PROJECT_DIR/$ENV_FILE"
    fi
}

preflight() {
    log_info "检查项目目录: $PROJECT_DIR"
    cd "$PROJECT_DIR"

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "环境文件不存在: $ENV_FILE"
        exit 1
    fi

    need_cmd docker
    if [[ "$SKIP_PULL" -eq 0 ]]; then
        need_cmd git
    fi

    if ! docker compose version >/dev/null 2>&1; then
        log_error "未检测到 docker compose 插件"
        exit 1
    fi

    COMPOSE=(docker compose --env-file "$ENV_FILE")
    if ! "${COMPOSE[@]}" config -q >/dev/null 2>&1; then
        log_error "docker compose 配置校验失败，请检查 $ENV_FILE 和 docker-compose.yml"
        exit 1
    fi

    local openai_api_key
    openai_api_key="$(get_env_value OPENAI_API_KEY "")"
    if [[ -z "$openai_api_key" || "$openai_api_key" == your_* || "$openai_api_key" == sk-your* ]]; then
        log_warning "OPENAI_API_KEY 看起来未配置为生产值，涉及问答/抽取能力可能不可用"
    fi

    OPENSPG_BASE_URL_CHECK="$(get_env_value OPENSPG_BASE_URL "http://172.17.0.1:8887")"
    BACKEND_PORT_CHECK="$(get_env_value BACKEND_PORT "8000")"
    FRONTEND_PORT_CHECK="$(get_env_value FRONTEND_PORT "8100")"
    OPENKS_FRONTEND_PORT_CHECK="$(get_env_value OPENKS_FRONTEND_PORT "8205")"
    FLOWER_PORT_CHECK="$(get_env_value FLOWER_PORT "5555")"
    NEO4J_HTTP_PORT_CHECK="$(get_env_value NEO4J_HTTP_PORT "7474")"
    KAG_MCP_PORT_CHECK="$(get_env_value KAG_MCP_PORT "3000")"

    log_info "部署环境文件: $ENV_FILE"
    log_info "OpenSPG 地址: $OPENSPG_BASE_URL_CHECK"
}

pull_latest() {
    if [[ "$SKIP_PULL" -eq 1 ]]; then
        log_info "已跳过 git pull（--skip-pull）"
        return 0
    fi

    local current_branch
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    log_info "当前分支: $current_branch"

    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "当前工作区存在未提交改动，git pull 可能失败"
    fi

    git pull --ff-only origin "$current_branch"
    log_success "代码拉取完成"

    log_info "最新提交:"
    git --no-pager log -1 --pretty=format:"%h - %an, %ad : %s" --date=iso
    echo ""
}

deploy_stack() {
    if [[ "$SKIP_DOWN" -eq 0 ]]; then
        log_info "停止容器..."
        "${COMPOSE[@]}" down
    else
        log_info "已跳过 down（--skip-down）"
    fi

    if [[ "$SKIP_BUILD" -eq 0 ]]; then
        log_info "重建后端镜像..."
        "${COMPOSE[@]}" build backend
        log_info "重建前端镜像..."
        "${COMPOSE[@]}" build frontend
        log_info "重建 OpenKS 前端镜像..."
        "${COMPOSE[@]}" build openks-frontend
        if [[ "$SKIP_KAG_MCP" -eq 0 ]]; then
            log_info "重建 KAG MCP 镜像..."
            "${COMPOSE[@]}" build kag-mcp
        fi
    else
        log_info "已跳过镜像构建（--skip-build）"
    fi

    if [[ "$SKIP_KAG_MCP" -eq 1 ]]; then
        local services
        mapfile -t services < <("${COMPOSE[@]}" config --services | grep -v '^kag-mcp$')
        log_info "启动服务（跳过 kag-mcp）..."
        "${COMPOSE[@]}" up -d "${services[@]}"
        "${COMPOSE[@]}" rm -sf kag-mcp >/dev/null 2>&1 || true
    else
        log_info "启动服务..."
        "${COMPOSE[@]}" up -d
    fi
}

post_checks() {
    log_info "服务状态:"
    "${COMPOSE[@]}" ps

    wait_http "http://127.0.0.1:${BACKEND_PORT_CHECK}/health" "后端健康检查" 25 3
    ensure_frontend_running
    wait_http "http://127.0.0.1:${FRONTEND_PORT_CHECK}/" "前端健康检查" 25 3
    wait_http "http://127.0.0.1:${OPENKS_FRONTEND_PORT_CHECK}/" "OpenKS 前端健康检查" 25 3
    if [[ "$SKIP_KAG_MCP" -eq 0 ]]; then
        wait_http "http://127.0.0.1:${KAG_MCP_PORT_CHECK}/sse" "KAG MCP 健康检查" 20 3 || true
    else
        log_info "已跳过 KAG MCP 健康检查（--skip-kag-mcp）"
    fi
    check_openspg "$OPENSPG_BASE_URL_CHECK" || true

    print_separator
    log_info "后端日志（最后 30 行）:"
    "${COMPOSE[@]}" logs --tail=30 backend || true

    print_separator
    local ip
    ip="$(get_ip)"
    log_success "部署流程完成"
    log_info "运行环境: $ENV_TYPE"
    log_info "服务访问地址:"
    echo "  - 前端: http://${ip}:${FRONTEND_PORT_CHECK}"
    echo "  - OpenKS 前端: http://${ip}:${OPENKS_FRONTEND_PORT_CHECK}"
    echo "  - 后端: http://${ip}:${BACKEND_PORT_CHECK}"
    if [[ "$SKIP_KAG_MCP" -eq 0 ]]; then
        echo "  - KAG MCP: http://${ip}:${KAG_MCP_PORT_CHECK}/sse"
    fi
    echo "  - Flower: http://${ip}:${FLOWER_PORT_CHECK}"
    echo "  - Neo4j: http://${ip}:${NEO4J_HTTP_PORT_CHECK}"
    echo ""
    log_info "实时日志:"
    echo "  docker compose --env-file \"$ENV_FILE\" logs -f backend"
    echo "  docker compose --env-file \"$ENV_FILE\" logs -f frontend"
    echo "  docker compose --env-file \"$ENV_FILE\" logs -f openks-frontend"
}

main() {
    parse_args "$@"

    print_separator
    log_info "开始部署智链机器人..."
    print_separator

    preflight
    pull_latest
    deploy_stack
    post_checks
}

trap 'log_error "部署过程中发生错误，请检查上方日志"; exit 1' ERR

main "$@"
