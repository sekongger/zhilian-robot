@echo off
REM 创建本体数据库和表结构 (Windows版本)

echo ==========================================
echo 创建本体数据库
echo ==========================================

REM 从环境变量或默认值获取MySQL连接信息
if "%MYSQL_HOST%"=="" set MYSQL_HOST=mysql
if "%MYSQL_PORT%"=="" set MYSQL_PORT=3306
if "%MYSQL_USER%"=="" set MYSQL_USER=root
if "%MYSQL_PASSWORD%"=="" set MYSQL_PASSWORD=password

echo 连接到MySQL服务器: %MYSQL_HOST%:%MYSQL_PORT%

REM 执行SQL脚本
mysql -h %MYSQL_HOST% -P %MYSQL_PORT% -u %MYSQL_USER% -p%MYSQL_PASSWORD% < scripts\init_ontology_tables.sql

if %ERRORLEVEL% EQU 0 (
    echo ✓ 数据库和表结构创建成功
) else (
    echo ✗ 创建失败，请检查MySQL连接配置
    exit /b 1
)

echo ==========================================
echo 完成
echo ==========================================

pause
