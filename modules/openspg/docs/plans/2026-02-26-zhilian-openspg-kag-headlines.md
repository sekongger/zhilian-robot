# 智链机器人 OpenSPG/KAG 产业头条演示 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `zhilian-robot` 前端新增“产业头条 + OpenSPG引擎演示”页面，复用现有真实资讯接入，提供 OpenSPG Schema/BuilderChain 模板与演示接口，并可在本地运行展示。

**Architecture:** 复用 `zhilian-robot` 的新闻采集与数据存储（MongoDB 中的 `crawled_articles` / `source_news`），新增一个后端“演示编排层”对新闻做规则事件聚合和头条评分，同时封装对 OpenSPG 的 API 调用（含离线 mock 回退）。前端新增一页双标签布局：业务侧展示产业头条与事件详情；引擎侧展示 Schema、Builder、Reason/Search/Graph 的演示结果与原始 JSON。

**Tech Stack:** FastAPI, React + Ant Design + Vite, Axios, pytest/FastAPI TestClient, MongoDB (optional), OpenSPG HTTP API

---

### Task 1: 设计与模板落地（OpenSPG Schema / BuilderChain / 桥接）

**Files:**
- Create: `zhilian-robot/backend/app/openspg_demo/schema_templates.py`
- Create: `zhilian-robot/backend/app/openspg_demo/builder_templates.py`
- Create: `zhilian-robot/backend/app/openspg_demo/bridge.py`
- Create: `zhilian-robot/backend/scripts/export_openspg_news_batch.py`

**Step 1: 写失败测试（模板结构）**

```python
def test_schema_template_contains_required_types():
    from app.openspg_demo.schema_templates import get_robot_chain_mvp_schema_template
    data = get_robot_chain_mvp_schema_template()
    labels = {item["label"] for item in data["types"]}
    assert "NewsArticle" in labels
    assert "IndustryEvent" in labels
    assert "Company" in labels
```

**Step 2: 运行测试确认失败**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_templates_test.py -q`
Expected: `ModuleNotFoundError` / import fail

**Step 3: 最小实现模板与桥接导出**
- 定义机器人主链 MVP 的类型/关系/索引字段模板（用于 OpenSPG Schema 演示）
- 定义 BuilderChain 节点模板（Normalize/Filter/Extract/Link/Merge/Sink）
- 提供新闻标准化导出为 JSONL 的函数（含 `doc_id/doc_hash/source_name/publish_time`）

**Step 4: 运行测试确认通过**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_templates_test.py -q`
Expected: PASS

**Step 5: Commit（可选，若本次不拆 commit 可跳过）**

```bash
git add docs/plans/... zhilian-robot/backend/app/openspg_demo zhilian-robot/backend/scripts/export_openspg_news_batch.py zhilian-robot/backend/tests/openspg_demo_templates_test.py
git commit -m "feat: add openspg kag schema and builder templates for demo"
```

### Task 2: 后端产业头条聚合服务（TDD）

**Files:**
- Create: `zhilian-robot/backend/app/openspg_demo/headlines_service.py`
- Create: `zhilian-robot/backend/tests/openspg_demo_headlines_service_test.py`

**Step 1: 写失败测试（事件聚合与评分）**

```python
def test_group_same_event_news_into_one_headline():
    from app.openspg_demo.headlines_service import build_headlines_from_news
    news = [...]
    result = build_headlines_from_news(news, top_n=10)
    assert len(result["headlines"]) == 1
    assert result["headlines"][0]["source_count"] == 2
```

**Step 2: 运行测试确认失败**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_headlines_service_test.py -q`
Expected: import fail / assertion fail

**Step 3: 最小实现**
- 规则事件识别（合作/融资/发布/订单/产能/政策）
- 实体抽取（标题关键词 + 简单正则/词表）
- `event_hash` 规则幂等键（事件类型 + 主体 + 客体 + 时间窗）
- 头条评分（新鲜度、事件权重、来源数）
- 返回头条列表、事件详情、统计摘要

**Step 4: 运行测试确认通过**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_headlines_service_test.py -q`
Expected: PASS

**Step 5: Commit（可选）**

```bash
git add zhilian-robot/backend/app/openspg_demo/headlines_service.py zhilian-robot/backend/tests/openspg_demo_headlines_service_test.py
git commit -m "feat: add industry headline aggregation service for kag demo"
```

### Task 3: 后端 OpenSPG 演示 API（TDD）

**Files:**
- Create: `zhilian-robot/backend/app/api/openspg_demo_routes.py`
- Modify: `zhilian-robot/backend/app/api/__init__.py`
- Create: `zhilian-robot/backend/app/openspg_demo/openspg_client.py`
- Create: `zhilian-robot/backend/tests/openspg_demo_api_test.py`

**Step 1: 写失败测试（核心接口）**

```python
def test_kag_headlines_demo_endpoint_returns_payload():
    client = TestClient(app)
    res = client.get("/api/v1/openspg-demo/headlines")
    assert res.status_code == 200
    assert "headlines" in res.json()
```

```python
def test_openspg_capability_demo_endpoint_returns_sections():
    client = TestClient(app)
    res = client.get("/api/v1/openspg-demo/engine/snapshot")
    data = res.json()
    assert "schema" in data and "builder" in data and "reason" in data and "search" in data and "graph" in data
```

**Step 2: 运行测试确认失败**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_api_test.py -q`
Expected: 404

**Step 3: 最小实现**
- `/openspg-demo/headlines`：从 `source_news` 或 `crawled_articles` 读取新闻，聚合头条（无库时回退样例）
- `/openspg-demo/headlines/{event_id}`：返回事件详情 + 证据新闻
- `/openspg-demo/engine/snapshot`：返回
- OpenSPG Schema 模板
- BuilderChain 模板
- Reason/Search/Graph 演示查询结果（调用 OpenSPG；失败则 mock）
- `/openspg-demo/engine/proxy/*`（可选）：透传 OpenSPG API 调试

**Step 4: 运行测试确认通过**

Run: `pytest zhilian-robot/backend/tests/openspg_demo_api_test.py -q`
Expected: PASS

**Step 5: Commit（可选）**

```bash
git add zhilian-robot/backend/app/api/openspg_demo_routes.py zhilian-robot/backend/app/openspg_demo zhilian-robot/backend/tests/openspg_demo_api_test.py zhilian-robot/backend/app/api/__init__.py
git commit -m "feat: add openspg kag demo backend APIs"
```

### Task 4: 前端 API 封装与页面（TDD-lite）

**Files:**
- Create: `zhilian-robot/frontend/src/services/openspgDemoApi.js`
- Create: `zhilian-robot/frontend/src/pages/OpenSPGKagHeadlinesPage.jsx`
- Modify: `zhilian-robot/frontend/src/App.jsx`
- Modify: `zhilian-robot/frontend/src/components/Layout.jsx`

**Step 1: 写失败测试（API封装）**

```javascript
import { openspgDemoService } from './openspgDemoApi'
import apiClient from '../utils/api'
vi.mock('../utils/api', () => ({ default: { get: vi.fn() } }))

test('getHeadlines calls correct endpoint', async () => {
  apiClient.get.mockResolvedValue({ headlines: [] })
  await openspgDemoService.getHeadlines()
  expect(apiClient.get).toHaveBeenCalledWith('/api/v1/openspg-demo/headlines', { params: {} })
})
```

**Step 2: 运行测试确认失败**

Run: `npm test` 不可用时改为 `vite build` + 手工 smoke（该项目未配置统一测试脚本）
Expected: 模块不存在/构建失败

**Step 3: 最小实现页面**
- 标签页 1：`产业头条`
- 顶部统计卡（24h资讯数、事件数、多源确认事件数）
- 头条表格/卡片
- 点击事件打开详情 Drawer（证据新闻、涉及实体、原始文本片段）
- 标签页 2：`OpenSPG引擎演示`
- Schema 结构预览
- BuilderChain 节点流程
- Reason/Search/Graph 查询结果（JSON + 简表）
- 刷新按钮重新拉取后端 snapshot

**Step 4: 构建验证**

Run: `cd zhilian-robot/frontend && npm run build`
Expected: build success

**Step 5: Commit（可选）**

```bash
git add zhilian-robot/frontend/src/pages/OpenSPGKagHeadlinesPage.jsx zhilian-robot/frontend/src/services/openspgDemoApi.js zhilian-robot/frontend/src/App.jsx zhilian-robot/frontend/src/components/Layout.jsx
git commit -m "feat: add openspg kag headlines demo page"
```

### Task 5: 本地运行与联调验证

**Files:**
- Modify (if needed): `zhilian-robot/backend/.env.example`（新增 OpenSPG base URL 配置说明）
- Create (optional): `zhilian-robot/docs/OPENSPG_KAG_HEADLINES_DEMO.md`

**Step 1: 后端启动前检查**
- 确认 Python 依赖安装完成
- 可选启动 MongoDB（无 Mongo 时接口走 demo fallback）

**Step 2: 启动后端**

Run: `cd zhilian-robot/backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`
Expected: FastAPI 启动成功

**Step 3: 启动前端**

Run: `cd zhilian-robot/frontend && npm run dev -- --host 127.0.0.1 --port 3000`
Expected: Vite 启动成功

**Step 4: 打开页面并验证**
- 页面路径：`/openspg-kag-headlines`（新增路由）
- 验证：
- 头条榜显示
- 事件详情可展开
- OpenSPG 引擎演示区可显示 Schema/Builder/Reason/Search/Graph snapshot

**Step 5: 若 OpenSPG 服务可用，验证真实调用**
- 启动 OpenSPG（或配置已运行实例）
- 设置 `OPENSPG_BASE_URL`
- 刷新页面确认 snapshot 切换为真实结果（非 mock）

**Step 6: 回归检查**

Run:
- `pytest zhilian-robot/backend/tests/openspg_demo_* -q`
- `cd zhilian-robot/frontend && npm run build`

Expected:
- 后端测试通过
- 前端构建通过

