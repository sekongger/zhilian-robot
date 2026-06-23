#!/bin/bash

# 创建本体数据库和表结构

echo "=========================================="
echo "创建本体数据库"
echo "=========================================="

# 从环境变量或默认值获取MySQL连接信息
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_PORT=${MYSQL_PORT:-3306}
MYSQL_USER=${MYSQL_USER:-root}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-password}

echo "连接到MySQL服务器: $MYSQL_HOST:$MYSQL_PORT"

# 执行SQL脚本
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" < /app/scripts/init_ontology_tables.sql

if [ $? -eq 0 ]; then
    echo "✓ 数据库和表结构创建成功"
else
    echo "✗ 创建失败，请检查MySQL连接配置"
    exit 1
fi

echo "=========================================="
echo "完成"
echo "=========================================="
