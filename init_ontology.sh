#!/bin/bash

###############################################################################
# 智链机器人 - 本体模型库初始化脚本
# 用途: 初始化V2本体模型库（ontology_schema_registry）
# 使用: 
#   bash init_ontology.sh          # 初始化（保留现有数据）
#   bash init_ontology.sh --reset  # 清空并重新初始化
#   bash init_ontology.sh --clean  # 仅清空数据
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 自动检测项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_separator() {
    echo "=============================================================================="
}

###############################################################################
# 清空本体表数据
###############################################################################

clean_ontology_data() {
    log_warning "正在清空所有本体表数据..."
    
    # 按依赖关系倒序清空：实例 -> 概念 -> 属性/公理/关系 -> 类 -> 元信息
    docker exec $MYSQL_CONTAINER mysql -u root -p${MYSQL_PWD} --default-character-set=utf8mb4 -e "
        SET NAMES utf8mb4;
        USE ontology_schema_registry;
        SET FOREIGN_KEY_CHECKS = 0;
        DELETE FROM inc_instance;
        DELETE FROM inc_concept;
        DELETE FROM inc_property;
        DELETE FROM inc_axiom;
        DELETE FROM inc_relation;
        DELETE FROM inc_class;
        DELETE FROM inc_ontology_meta;
        SET FOREIGN_KEY_CHECKS = 1;
    " 2>/dev/null
    
    log_success "本体表数据已清空"
}

###############################################################################
# 主流程
###############################################################################

main() {
    # 解析参数
    RESET_MODE=false
    CLEAN_ONLY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --reset)
                RESET_MODE=true
                shift
                ;;
            --clean)
                CLEAN_ONLY=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                echo "使用方法:"
                echo "  bash init_ontology.sh          # 初始化（保留现有数据）"
                echo "  bash init_ontology.sh --reset  # 清空并重新初始化"
                echo "  bash init_ontology.sh --clean  # 仅清空数据"
                exit 1
                ;;
        esac
    done
    print_separator
    log_info "开始初始化本体模型库..."
    print_separator
    
    cd "$PROJECT_DIR"
    
    # 1. 检查SQL文件是否存在
    log_info "检查SQL脚本文件..."
    
    if [ ! -f "backend/scripts/init_ontology_tables.sql" ]; then
        log_error "找不到建表脚本: backend/scripts/init_ontology_tables.sql"
        exit 1
    fi
    
    if [ ! -f "backend/scripts/init_ontology_data.sql" ]; then
        log_error "找不到数据脚本: backend/scripts/init_ontology_data.sql"
        exit 1
    fi
    
    log_success "SQL脚本文件检查完成"
    
    # 2. 获取MySQL容器
    print_separator
    log_info "检查MySQL容器状态..."
    
    MYSQL_CONTAINER=$(docker compose ps -q mysql 2>/dev/null)
    
    if [ -z "$MYSQL_CONTAINER" ]; then
        log_error "MySQL容器未运行，请先启动服务: docker compose up -d mysql"
        exit 1
    fi
    
    log_success "MySQL容器运行中: $MYSQL_CONTAINER"
    
    # 3. 从.env读取MySQL密码
    if [ -f ".env" ]; then
        source .env 2>/dev/null || true
    fi
    
    MYSQL_PWD=${MYSQL_PASSWORD:-password}
    
    # 4. 如果仅清空模式，执行清空后退出
    if [ "$CLEAN_ONLY" = true ]; then
        print_separator
        clean_ontology_data
        print_separator
        log_success "清空完成！"
        exit 0
    fi
    
    # 5. 如果重置模式，先清空数据
    if [ "$RESET_MODE" = true ]; then
        print_separator
        clean_ontology_data
    fi
    
    # 6. 复制SQL文件到容器
    print_separator
    log_info "复制SQL文件到MySQL容器..."
    
    docker cp backend/scripts/init_ontology_tables.sql $MYSQL_CONTAINER:/tmp/
    docker cp backend/scripts/init_ontology_data.sql $MYSQL_CONTAINER:/tmp/
    
    log_success "SQL文件复制完成"
    
    # 7. 执行建表脚本
    print_separator
    log_info "创建本体模型库和表结构..."
    
    docker exec $MYSQL_CONTAINER mysql -u root -p${MYSQL_PWD} --default-character-set=utf8mb4 -e "source /tmp/init_ontology_tables.sql" 2>/dev/null
    
    log_success "本体模型库和表结构创建完成"
    
    # 8. 执行数据初始化脚本
    print_separator
    log_info "初始化本体模型数据..."
    
    docker exec $MYSQL_CONTAINER mysql -u root -p${MYSQL_PWD} --default-character-set=utf8mb4 -e "source /tmp/init_ontology_data.sql" 2>/dev/null
    
    log_success "本体模型数据初始化完成"
    
    # 9. 验证初始化结果
    print_separator
    log_info "验证初始化结果..."
    
    echo ""
    log_info "数据库表统计:"
    docker exec $MYSQL_CONTAINER mysql -u root -p${MYSQL_PWD} --default-character-set=utf8mb4 -e "
        USE ontology_schema_registry;
        SELECT 'inc_ontology_meta' as table_name, COUNT(*) as count FROM inc_ontology_meta
        UNION ALL
        SELECT 'inc_class', COUNT(*) FROM inc_class
        UNION ALL
        SELECT 'inc_property', COUNT(*) FROM inc_property
        UNION ALL
        SELECT 'inc_relation', COUNT(*) FROM inc_relation
        UNION ALL
        SELECT 'inc_axiom', COUNT(*) FROM inc_axiom
        UNION ALL
        SELECT 'inc_concept', COUNT(*) FROM inc_concept
        UNION ALL
        SELECT 'inc_instance', COUNT(*) FROM inc_instance;
    " 2>/dev/null
    
    # 10. 完成
    print_separator
    log_success "本体模型库初始化完成！"
    print_separator
    
    echo ""
    log_info "初始化内容:"
    echo "  - 本体模型信息: 1条"
    echo "  - 类定义: 22+条（5核心类 + 4支撑类 + 子类）"
    echo "  - 属性定义: 17+条"
    echo "  - 关系定义: 16+条"
    echo "  - 公理规则: 11条"
    echo "  - 产业概念: 8+条"
    echo ""
    log_info "验证API:"
    echo "  curl http://localhost:8000/api/v1/ontology/meta"
    echo "  curl http://localhost:8000/api/v1/ontology/statistics"
    echo ""
    log_info "访问前端本体管理页面:"
    echo "  http://localhost:8100/ontology"
    echo ""
}

###############################################################################
# 执行
###############################################################################

trap 'log_error "初始化过程中发生错误"; exit 1' ERR

main "$@"

exit 0
