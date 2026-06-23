@echo off
REM 综合修复脚本 - 修复所有数据层 (Windows版本)

echo ==========================================
echo 数据海平台 - 数据层综合修复
echo ==========================================

cd /d "%~dp0\.."

echo.
echo 步骤 1/2: 修复数据资源层...
python scripts\fix_data_resource_layer.py

echo.
echo 步骤 2/2: 初始化本体模型库...
python scripts\init_ontology_minimal.py

echo.
echo ==========================================
echo 修复完成！请刷新前端页面查看结果
echo ==========================================

pause
