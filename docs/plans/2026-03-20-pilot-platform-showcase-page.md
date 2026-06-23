# Pilot Platform Showcase Page Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 `/platform` 中试平台页改造成基于设计文档的前台展示页，保留“整体概况 / 数据汇聚 / 知识计算 / 网链分析 / 智能服务”五个一级菜单，所有外部能力先以“后续接入”占位展示。

**Architecture:** 页面继续复用现有 `/platform` 路由和顶部五个 Tab，但不再依赖外部接口返回实时数据来组织主体内容，而是以静态展示模型驱动页面模块。展示模型负责统一管理每个栏目下的概览、模块卡片、流程、占位标识和跳转入口，页面层只负责渲染与交互。

**Tech Stack:** React 18, Ant Design 5, Vite, node:test

---

### Task 1: 锁定新的展示模型与占位规则

**Files:**
- Create: `frontend/src/pages/platformShowcaseModel.mjs`
- Test: `frontend/tests/platformShowcaseModel.test.mjs`

**Step 1: Write the failing test**

写测试校验：
- 五个一级栏目都存在
- 每个栏目包含设计文档要求的关键模块
- 所有需要外部接入的卡片带有“后续接入”或等价占位状态

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/platformShowcaseModel.test.mjs`
Expected: FAIL because `platformShowcaseModel.mjs` does not exist yet

**Step 3: Write minimal implementation**

实现一个静态展示模型，导出栏目定义、模块卡片、流程节点、状态标识与占位文案。

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/platformShowcaseModel.test.mjs`
Expected: PASS

### Task 2: 锁定新的页面文案与结构

**Files:**
- Modify: `frontend/tests/platformOverviewPageCopy.test.mjs`
- Create: `frontend/tests/platformOverviewShowcaseLayout.test.mjs`
- Modify: `frontend/src/pages/PlatformOverviewPage.jsx`

**Step 1: Write the failing test**

补测试校验：
- 页面源码中存在“五个一级菜单对应的展示标题”
- 页面包含“后续接入”占位标识
- 页面包含“数据资源池 / 产业网链大图 / 四链分析 / 头条推送”等前台成果词汇

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/platformOverviewPageCopy.test.mjs frontend/tests/platformOverviewShowcaseLayout.test.mjs`
Expected: FAIL because current page仍以旧的实时总览结构为主

**Step 3: Write minimal implementation**

重写 `/platform` 页面主结构：
- 顶部保留五个 Tab 的导航逻辑
- 主体按栏目渲染展示模块
- 对外部接入能力统一显示占位卡片与后续接入标识
- 保留少量可用跳转按钮，但不发起真实接入读取

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/platformOverviewPageCopy.test.mjs frontend/tests/platformOverviewShowcaseLayout.test.mjs`
Expected: PASS

### Task 3: 补视觉与响应式样式

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/pages/PlatformOverviewPage.jsx`

**Step 1: Write the failing test**

通过页面结构测试锁定新的模块层级和占位样式类名，例如展示分区、占位徽标、流程时间线、模块卡片。

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/platformOverviewShowcaseLayout.test.mjs`
Expected: FAIL because new class names and structure are absent

**Step 3: Write minimal implementation**

新增样式，确保：
- 页面具备清晰的展示分区
- 移动端下模块能折叠为单列
- “后续接入”占位视觉统一

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/platformOverviewShowcaseLayout.test.mjs`
Expected: PASS

### Task 4: 运行整体验证

**Files:**
- Modify: `frontend/src/pages/platformTabs.mjs` (if copy needs alignment)
- Verify: `frontend/package.json`

**Step 1: Run focused test suite**

Run: `node --test frontend/tests/platformTabs.test.mjs frontend/tests/platformOverviewPageCopy.test.mjs frontend/tests/platformOverviewShowcaseLayout.test.mjs frontend/tests/platformShowcaseModel.test.mjs`
Expected: PASS

**Step 2: Run production build**

Run: `npm run build`
Workdir: `frontend`
Expected: build succeeds with exit code 0
