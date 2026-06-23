# OpenKS Pilot Platform Production Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 对齐 AI 中试平台、OpenKS 工作台和 DataHub/Graphiti/OpenSPG 主链口径，把独立域名跳转、接口规范展示、mock 头条接口和产业网图谱审核说明一起落地。

**Architecture:** 前台 `/platform` 保持“前台展示页”定位，但补充明确的接口合同、独立域名、主链状态和审核说明；OpenKS 工作台继续消费真实后端接口，并增加对主链生产化状态与接入边界的表达；后端补齐 DataHub mock 头条接口契约和必要的 OpenKS 概览字段，确保页面不是纯静态文案。

**Tech Stack:** React + Ant Design + Vite、FastAPI、pytest、node:test

---

### Task 1: 独立域名与前台展示口径

**Files:**
- Modify: `frontend/src/utils/openksPortal.js`
- Modify: `frontend/src/pages/platformShowcaseModel.mjs`
- Modify: `frontend/src/pages/PlatformOverviewPage.jsx`
- Modify: `frontend/src/index.css`
- Test: `frontend/tests/openksWorkbenchNavigation.test.mjs`
- Test: `frontend/tests/platformShowcaseModel.test.mjs`
- Test: `frontend/tests/platformOverviewPageCopy.test.mjs`

**Step 1: 写失败测试**

为以下行为补测试：
- OpenKS 门户跳转默认落到独立域名
- 中试平台页面出现 DataHub / Graphiti / OpenSPG 主链与审核说明
- 页面文案明确“独立域名”“接口定义”“审核机制”

**Step 2: 跑测试确认失败**

Run: `cd frontend && node --test tests/openksWorkbenchNavigation.test.mjs tests/platformShowcaseModel.test.mjs tests/platformOverviewPageCopy.test.mjs`

Expected: FAIL because current model/page 还没有这些字段与文案。

**Step 3: 写最小实现**

- 给 `openksPortal` 增加独立域名默认值，同时保留环境变量覆盖
- 扩展平台展示模型，增加接口合同、链路状态、审核与优化说明
- 在 `PlatformOverviewPage.jsx` 中渲染新说明块
- 补相应样式

**Step 4: 跑测试确认通过**

Run: `cd frontend && node --test tests/openksWorkbenchNavigation.test.mjs tests/platformShowcaseModel.test.mjs tests/platformOverviewPageCopy.test.mjs`

Expected: PASS

### Task 2: DataHub mock 接口契约与 OpenKS 工作台说明

**Files:**
- Modify: `backend/app/services/datahub_mock_service.py`
- Modify: `backend/app/api/datahub_mock_routes.py`
- Modify: `backend/app/api/openks_routes.py`
- Modify: `frontend/src/services/openksWorkbenchApi.js`
- Modify: `frontend/src/pages/OpenKSWorkbenchPage.jsx`
- Test: `backend/tests/datahub_mock_routes_test.py`
- Test: `backend/tests/openks_routes_test.py`
- Test: `frontend/tests/openksWorkbenchDataBinding.test.mjs`

**Step 1: 写失败测试**

为以下行为补测试：
- `GET /api/v1/datahub/mock/headlines` 返回接口版本、字段规范、OpenKS 对接说明和 mock 数据
- `GET /api/v1/openks/overview` 或相关工作台数据返回主链生产化状态
- OpenKS 工作台页面代码包含 DataHub / Graphiti / OpenSPG 主链说明

**Step 2: 跑测试确认失败**

Run: `cd backend && pytest tests/datahub_mock_routes_test.py tests/openks_routes_test.py -q`

Run: `cd frontend && node --test tests/openksWorkbenchDataBinding.test.mjs`

Expected: FAIL because current接口与页面还没有完整合同/主链说明。

**Step 3: 写最小实现**

- 在 DataHub mock 服务里补头条接口规范和标准字段说明
- 在 OpenKS 概览接口中补主链状态、上游边界、Graphiti/DataHub 接入策略
- 更新工作台页面展示这些信息

**Step 4: 跑测试确认通过**

Run: `cd backend && pytest tests/datahub_mock_routes_test.py tests/openks_routes_test.py -q`

Run: `cd frontend && node --test tests/openksWorkbenchDataBinding.test.mjs`

Expected: PASS

### Task 3: 全链路验证与结论整理

**Files:**
- Review: `backend/app/services/openks_build_job_service.py`
- Review: `backend/app/openspg_demo/bridge_runner.py`
- Review: `backend/app/openspg_demo/graph_materializer.py`
- Review: `supxmind/supxmind-openks/openks/cross/*.py`
- Review: `supxmind/supxmind-openks/openks/kg/fact/event_kg/**`
- Review: `supxmind/supxmind-openks/openks/kg/fact/industry_network/**`

**Step 1: 运行聚焦验证**

Run: `cd backend && pytest tests/datahub_mock_routes_test.py tests/openks_routes_test.py tests/openks_schema_runtime_service_test.py tests/openspg_graph_materializer_test.py tests/openspg_demo_bridge_runner_test.py -q`

Run: `cd frontend && node --test tests/openksWorkbenchNavigation.test.mjs tests/openksWorkbenchDataBinding.test.mjs tests/platformShowcaseModel.test.mjs tests/platformOverviewPageCopy.test.mjs tests/platformOverviewShowcaseLayout.test.mjs`

Expected: PASS

**Step 2: 对照需求逐条验收**

- 独立域名跳转是否生效
- DataHub 是否明确“暂不实接，仅提供接口规范 + mock 头条”
- Graphiti 是否明确“暂不实接，仅提供合同与后续接入说明”
- OpenSPG 是否被表达为主生产链
- 页面是否明确产业网大图的构建、审核与优化建议

**Step 3: 汇总链路分析**

输出：
- 当前 AI 中试平台 / OpenKS / OpenSPG / Graphiti / DataHub 实现边界
- 当前主链真实代码路径
- 产业网大图当前构建方式、正确性风险、审核方法和后续优化建议
