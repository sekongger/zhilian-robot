#!/usr/bin/env bash

###############################################################################
# 智链机器人 - 本地联调重建脚本
# 用途: 在本机使用 .env.remote 重建容器，直连远端依赖做联调
# 注意: 该脚本不会把代码同步到线上服务器
# 使用:
#   bash scripts/redeploy-remote.sh
#   bash scripts/redeploy-remote.sh --skip-build
###############################################################################

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env.remote"
DEPLOY_SCRIPT="$PROJECT_DIR/deploy.sh"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "未找到环境文件: $ENV_FILE"
    echo "请先创建 .env.remote 后再执行。"
    exit 1
fi

if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
    echo "未找到部署脚本: $DEPLOY_SCRIPT"
    exit 1
fi

bash "$DEPLOY_SCRIPT" --env-file "$ENV_FILE" --skip-pull "$@"
