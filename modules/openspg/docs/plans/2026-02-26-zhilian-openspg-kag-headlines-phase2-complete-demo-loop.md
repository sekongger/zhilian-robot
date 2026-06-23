# 智链机器人 OpenSPG/KAG 产业头条完整演示闭环（二期）Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在现有演示基础上补齐完整闭环：接入真实 OpenSPG 实例状态与导入入口、实现 zhilian-robot 到 OpenSPG 的半实时桥接运行器、增加独立事件详情/证据追溯页并完成本地联调验证。

**Architecture:** 保留现有 `openspg_demo` 双标签页结构，后端新增桥接运行器（增量游标 + 批次落盘 + 可选提交 OpenSPG Builder KAG 任务）与 OpenSPG 管理接口（健康检查、Builder 任务提交/查询）。前端新增独立事件详情页和桥接运行面板，让“采集 -> 桥接 -> OpenSPG -> 头条/详情”流程可演示、可追溯、可回放。

**Tech Stack:** FastAPI, React + React Router + Ant Design, pytest, httpx, Docker Compose (OpenSPG), JSONL batch files

---

### Task 1: 后端测试先行（桥接运行器与管理接口）

**Files:**
- Modify: `zhilian-robot/backend/tests/openspg_demo_api_test.py`
- Create: `zhilian-robot/backend/tests/openspg_demo_bridge_runner_test.py`

**Step 1: 写失败测试**
- 桥接运行器可创建批次并返回 `run_id/status/file_path`
- 可读取桥接运行状态（最近批次、数据源、导出条数）
- OpenSPG 管理接口返回健康探测与配置状态
- Builder 提交接口在 mock client 下返回结构化结果

**Step 2: 跑测试确认失败**

Run: `cd zhilian-robot/backend && pytest tests/openspg_demo_api_test.py tests/openspg_demo_bridge_runner_test.py -q`
Expected: 404 / import fail / assertion fail

**Step 3: 最小实现通过**
- 新增桥接运行器模块与状态文件
- 新增 API：`/openspg-demo/bridge/status`、`/openspg-demo/bridge/run`
- 新增 API：`/openspg-demo/engine/health`、`/openspg-demo/engine/builder/submit`

**Step 4: 复跑测试为绿**

Run: `cd zhilian-robot/backend && pytest tests/openspg_demo_api_test.py tests/openspg_demo_bridge_runner_test.py -q`
Expected: PASS

### Task 2: 后端实现半实时桥接（增量游标 + 批次落盘 + 可选 Builder 提交）

**Files:**
- Create: `zhilian-robot/backend/app/openspg_demo/bridge_runner.py`
- Modify: `zhilian-robot/backend/app/openspg_demo/routes.py`
- Modify: `zhilian-robot/backend/app/openspg_demo/openspg_client.py`

**Step 1: 增量游标与批次落盘**
- 状态目录：`zhilian-robot/backend/data/openspg_demo/`
- 状态文件：`bridge_state.json`
- 批次目录：`batches/*.jsonl`
- 支持 `force_full`、`limit`、`since` 模式

**Step 2: OpenSPG 健康与 Builder 提交**
- `engine/health`：探测 OpenSPG base URL 可用性及关键接口状态
- `engine/builder/submit`：组装 `KagBuilderRequest`（命令模板 + JSONL 路径/URL），失败时结构化返回

**Step 3: 运行器 API 输出结构稳定**
- 返回 `run_id`、`export_count`、`cursor`、`builder_submit_result`、`batch_download_url`

### Task 3: 前端独立事件详情页与桥接运行面板

**Files:**
- Create: `zhilian-robot/frontend/src/pages/OpenSPGKagHeadlineEventDetailPage.jsx`
- Modify: `zhilian-robot/frontend/src/pages/OpenSPGKagHeadlinesPage.jsx`
- Modify: `zhilian-robot/frontend/src/services/openspgDemoApi.js`
- Modify: `zhilian-robot/frontend/src/App.jsx`

**Step 1: 页面行为**
- 头条列表支持“查看详情页”
- 详情页展示：事件概要、证据新闻、原始 JSON、OpenSPG 查询辅助面板

**Step 2: 桥接运行面板**
- 显示桥接状态（最近运行、批次文件、导出条数、数据源）
- 支持手动触发桥接批次
- 可选触发 Builder 提交（若 OpenSPG 在线）

**Step 3: 引擎实况面板增强**
- 显示 `engine/health` 结果和在线状态标签
- `engine/snapshot` 面板标识 live/mock

### Task 4: 本地联调与闭环验证

**Files:**
- Modify: `docs/plans/2026-02-26-zhilian-openspg-kag-headlines.md`（可补充链接）
- (可选) Create: `zhilian-robot/docs/OPENSPG_KAG_HEADLINES_PHASE2_RUNBOOK.md`

**Step 1: 尝试拉起 OpenSPG**

Run: `docker compose -f dev/release/docker-compose.yml up -d`
Expected: `server/mysql/neo4j/minio` 启动（若镜像拉取失败，记录失败原因并保持 mock 演示可用）

**Step 2: 后端/前端验证**

Run:
- `cd zhilian-robot/backend && pytest tests/openspg_demo_* -q`
- `cd zhilian-robot/frontend && npm run build`
- `curl http://127.0.0.1:8000/api/v1/openspg-demo/bridge/status`
- `curl -X POST http://127.0.0.1:8000/api/v1/openspg-demo/bridge/run`

Expected:
- 测试通过
- 构建成功
- 桥接运行产生 JSONL 批次
- OpenSPG 在线时 `engine/health` 为 live；离线时返回结构化降级信息

