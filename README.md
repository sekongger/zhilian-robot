# 智链机器人 - 大模型驱动的产业链图谱自动构建平台

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)
[![React](https://img.shields.io/badge/react-18.2-blue.svg)](https://react.dev/)

## 📖 项目简介

智链机器人是一个基于 **DeepSeek 大语言模型**的产业链知识图谱自动构建与分析平台，专注于机器人及相关产业链的智能数据采集、NLP 分析和交互式可视化展示。系统采用前后端分离架构，支持自动化数据采集、实时图谱构建和 **D3.js 力导向图**可视化。

### 🎯 核心特性

- ✅ **深色主题 UI**：现代化深色界面设计，专业数据可视化体验
- ✅ **D3.js 力导向图**：支持节点拖拽、缩放、全屏展示，集成动量热度可视化
- ✅ **动量热度系统**：实时计算实体热度，节点颜色渐变（蓝→绿→橙→红）+ 光环脉动 + 粒子流动
- ✅ **情报溯源机制**：可追溯每个实体的数据来源，展示引用次数和相关证据链
- ✅ **统计仪表盘**：Recharts 驱动的饼图/柱状图实时统计
- ✅ **DeepSeek LLM**：智能实体识别和关系抽取
- ✅ **自动化采集**：RSS 订阅 + 定时爬虫 + Celery 任务调度
- ✅ **Neo4j 图数据库**：高性能知识图谱存储与查询
- ✅ **Docker 一键部署**：9 个容器编排，生产环境就绪

---

## 🚀 快速开始

### 前置要求

- **Docker Desktop** 4.0+ (Windows/Mac) 或 **Docker Engine** 20.10+ (Linux)
- **Docker Compose** 2.0+
- **Git**

> **🔐 安全提示**：本项目内置了演示用的 API 密钥，可直接运行。生产环境部署时请务必修改所有密钥，详见 [SECURITY.md](SECURITY.md)

### 部署步骤

#### 1️⃣ 克隆项目

```bash
git clone https://github.com/Aspirin-s/zhilian-robot.git
cd zhilian-robot
```

#### 2️⃣ 启动所有服务

> **⚠️ 注意**：项目已内置 DeepSeek API 密钥（演示用），可直接启动使用！  
> 如需使用您自己的密钥，请编辑 `backend/.env` 文件修改 `OPENAI_API_KEY` 参数。

```bash
# 一键启动 9 个容器（首次构建需 5-10 分钟）
docker-compose up -d

# 查看容器状态
docker-compose ps
```

#### 3️⃣ 访问应用

| 服务 | 地址 | 说明 |
|-----|------|-----|
| **前端应用** | http://localhost | 主界面（React + D3.js） |
| **后端 API** | http://localhost:8000 | FastAPI 接口文档 |
| **Neo4j 浏览器** | http://localhost:7474 | 图数据库管理（用户名: neo4j, 密码: password123） |
| **Flower 监控** | http://localhost:5555 | Celery 任务监控 |

---

## ✨ 功能模块

### 1. 📊 概览页

- 统计卡片：实时显示图谱节点数、关系数、知识库文章数
- Hero 渐变卡片：紫色渐变背景展示项目介绍
- 功能导航：快速跳转到图谱探索、智能分析、数据中心

### 2. 🕸️ 图谱探索

- **D3.js 力导向图**：节点拖拽、画布缩放（0.1x-4x）、全屏模式
- **动量热度可视化**：
  - 节点颜色渐变：动量0-100%对应蓝→绿→橙→红
  - 高动量节点（>60%）：红色虚线光环脉动效果
  - 中高动量节点（40-60%）：节点缩放脉动
  - 粒子流动：连接线上粒子从低动量流向高动量节点
  - 连接线渐变：基于两端节点动量的颜色渐变
- **搜索控制面板**：企业名称搜索 + 层级选择器（1-4 层关系）
- **统计仪表盘**：饼图（实体类型分布）+ 柱状图（Top 6 连接数节点）
- **实体详情面板**：查看节点信息、关联关系、动量值和引用次数

### 3. 🤖 智能分析

- **文本输入**：支持粘贴行业新闻、研报摘要、公司公告
- **DeepSeek LLM**：智能实体识别（NER）+ 关系抽取（RE）
- **结果可视化**：按类型分组的实体 Tags，箭头可视化的关系链
- **保存到图谱**：一键将分析结果存储到 Neo4j

### 4. 📊 动态分析（时间轴）

- **动量排行榜**：实时显示TOP实体动量热度，支持按类型筛选
- **时间轴可视化**：Recharts折线图展示实体动量历史趋势
- **情报溯源**：点击实体可查看所有相关文档、来源和引用证据
- **特别关注**：将高动量实体加入监控面板，自动提醒波动
- **数据透明性**：每个实体显示引用次数，确保数据可信度

### 5. 💾 数据中心

- **统计卡片**：总文章数、今日采集、数据源数、失败任务
- **RSS 订阅源管理**：批量更新、查看详情、删除失效源
- **文章列表管理**：搜索、分页、批量删除、单篇 NLP 分析
- **任务历史记录**：Celery 任务状态监控（成功/失败/运行中）
- **来源可信度**：每条数据记录来源标签（百度资讯/OFweek等）和原文链接

---

## 🛠️ 技术栈

### 前端技术

| 技术 | 版本 | 用途 |
|-----|------|-----|
| React | 18.2.0 | 前端框架 |
| Ant Design | 5.11.5 | UI 组件库（深色主题） |
| D3.js | 7.9.0 | 力导向图可视化 |
| Recharts | 2.15.4 | 统计图表（饼图/柱状图） |
| React Router | 6.20.0 | 单页应用路由 |
| Axios | 1.6.2 | HTTP 客户端 |
| Vite | 5.4.21 | 构建工具 |

### 后端技术

| 技术 | 版本 | 用途 |
|-----|------|-----|
| FastAPI | 0.104.1 | Web 框架 |
| Python | 3.9-slim | 运行环境 |
| OpenAI SDK | 1.57.0 | DeepSeek API 调用 |
| Celery | 5.3.4 | 分布式任务队列 |
| Scrapy | 2.11.0 | 爬虫框架 |
| Feedparser | 6.0.10 | RSS 解析 |

### 数据存储

| 数据库 | 版本 | 用途 |
|-------|------|-----|
| Neo4j | 5.20 | 知识图谱存储 |
| MongoDB | 8.0 | 文章和 RSS 数据 |
| MySQL | 8.0 | 任务配置和元数据 |
| Redis | 7-alpine | Celery broker + 缓存 |
| MinIO | latest | 原始文件对象存储 |

---

## 📁 项目结构

```plaintext
zhilian-robot/
├── backend/                      # 后端服务
│   ├── app/
│   │   ├── api/                 # FastAPI 路由
│   │   ├── analytics/           # 动量计算与异常检测
│   │   ├── nlp/                 # NLP 处理（DeepSeek LLM）
│   │   ├── services/            # 业务逻辑（Neo4j 图谱服务、实体规范化）
│   │   ├── crawler/             # 数据采集（RSS + 新闻爬虫）
│   │   ├── ingestion/           # 📦 数据接入（文件/API/流式）
│   │   ├── processing/          # 🔧 数据清洗与标准化
│   │   ├── tasks/               # Celery 异步任务
│   │   ├── database/            # 数据库连接（Neo4j/MongoDB/Redis/MinIO）
│   │   └── models/              # Pydantic 数据模型
│   ├── scripts/                 # 后台维护脚本
│   │   ├── init_sources.py     # 初始化数据源可信度
│   │   ├── backfill_momentum_history.py  # 回填历史动量数据
│   │   └── check_code_integrity.py       # 代码完整性检查
│   ├── config/                  # 配置文件
│   ├── wait_for_db.py          # 数据库启动等待脚本
│   ├── requirements.txt         # Python 依赖
│   └── Dockerfile               # 后端容器构建
│
├── frontend/                     # 前端服务
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   │   ├── HomePage.jsx            # 首页概览
│   │   │   ├── GraphPage.jsx           # 图谱探索（含动量可视化）
│   │   │   ├── AnalysisPage.jsx        # 智能分析
│   │   │   ├── TemporalAnalysisPage.jsx # 动态分析（时间轴+情报溯源）
│   │   │   └── DataManagePage.jsx      # 数据中心
│   │   ├── components/          # 组件库
│   │   │   ├── D3ForceGraph.jsx        # D3力导向图（含粒子效果）
│   │   │   ├── DashboardStats.jsx      # 统计卡片
│   │   │   ├── TimelineView.jsx        # 时间轴组件
│   │   │   └── Layout.jsx              # 布局框架
│   │   ├── services/            # API 服务
│   │   └── index.css            # 全局样式（深色主题）
│   ├── package.json             # npm 依赖
│   ├── vite.config.js           # Vite 配置
│   ├── Dockerfile               # 前端容器构建
│   └── nginx.conf               # Nginx 配置
│
├── docs/                         # 文档目录
│   ├── QUICKSTART.md            # 快速开始指南
│   └── DEPLOYMENT_CHECKLIST.md # 部署检查清单
│
├── docker-compose.yml           # 容器编排配置
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
└── README.md                    # 本文件
```

---

## 🔄 自动化任务

系统启动后，Celery Beat 会自动执行以下定时任务：

- **每日 02:00** - 爬取全量新闻
- **每 6 小时** - RSS 增量更新
- **每周一 03:00** - 清理 30 天前旧数据

可通过 Flower 监控面板（http://localhost:5555）查看任务状态。

---

## 🔧 常用命令

```bash
# 查看容器日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery-worker

# 重启服务
docker-compose restart backend
docker-compose restart frontend

# 重新构建镜像
docker-compose build --no-cache backend
docker-compose build --no-cache frontend

# 停止所有服务
docker-compose down

# 进入容器调试
docker exec -it zhilian-backend bash
docker exec -it zhilian-frontend sh
```

---

## 🐛 故障排查

### 前端显示空白页

```bash
# 检查浏览器控制台错误
# 重新构建前端
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### 后端容器无法启动

```bash
# 检查数据库连接日志
docker-compose logs backend | grep "Database"

# 确保数据库容器已启动
docker-compose ps neo4j mongodb redis
```

### DeepSeek API 调用失败

```bash
# 检查环境变量
docker exec zhilian-backend printenv | grep DEEPSEEK

# 重新配置并重启
vim backend/.env
docker-compose restart backend
```

更多问题请查看 [快速开始.md](docs/快速开始.md)

---

## 📊 项目状态

| 模块 | 完成度 | 说明 |
|-----|--------|-----|
| 数据采集 | 85% | ✅ RSS + 新闻爬虫 ✅ 来源标记 ⚠️ 缺少PDF报告解析 |
| NLP 分析 | 95% | ✅ DeepSeek LLM ✅ 实体/关系抽取 |
| 知识图谱 | 90% | ✅ Neo4j 存储 ✅ Cypher 查询 ✅ 实体规范化 |
| 动量系统 | 95% | ✅ 实时计算 ✅ 历史趋势 ✅ 异常检测 |
| 可视化 | 98% | ✅ D3力导向图 ✅ 动量热度 ✅ 粒子效果 ✅ 时间轴 |
| 情报溯源 | 90% | ✅ 引用统计 ✅ 证据链路 ✅ 来源可信度 |
| 前端界面 | 95% | ✅ D3.js ✅ 深色主题 ✅ 响应式 |
| 任务调度 | 90% | ✅ Celery ✅ 定时任务 ✅ Flower |
| 容器化 | 100% | ✅ Docker Compose ✅ 生产就绪 |

---

## 📄 开源许可

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) - 强大的大语言模型
- [Neo4j](https://neo4j.com/) - 图数据库支持
- [D3.js](https://d3js.org/) - 数据可视化库
- [Ant Design](https://ant.design/) - React UI 组件库
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架

---

<p align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给我们一个 Star！</strong>
</p>
