# Graphiti 行业知识图谱 API

本项目是一个强大的API，用于构建和分析面向特定行业的知识图谱。它借助 `graphiti-core` 并利用大型语言模型（LLM）的能力，从非结构化文本中自动提取实体和关系，并将它们存储在 Neo4j 图数据库中。随后，系统会执行高级图分析，以获得实体影响力、产业社群和热点趋势等深度洞察。

## 核心功能

-   **自动化知识抽取**: 能接收非结构化文本，并根据详细、自定义的 Pydantic Schema (`schemas/knowledge_schema.py`) 自动构建一个内容丰富的知识图谱。
-   **高级知识计算**:
    -   **PageRank**: 计算网络中每个实体的“核心影响力”。
    -   **Louvain 社群发现**: 识别关联紧密的实体集群，即“产业社群”。
    -   **动量得分 (Momentum Score)**: 一个自定义指标，用于追踪实体的“热度”或近期活跃程度。
-   **API 驱动**: 一个健壮的 FastAPI 后端，提供了用于数据录入、触发计算和查询结果的API接口。
-   **容器化环境**: 整个应用（FastAPI 后端、带有GDS插件的Neo4j数据库）都已通过 Docker 容器化，可通过一个命令轻松完成安装和一致性部署。

## 技术栈

-   **后端**: Python 3.12, FastAPI
-   **数据库**: Neo4j 5.26
-   **图分析**: Neo4j Graph Data Science (GDS)
-   **知识抽取**: `graphiti-core`
-   **容器化**: Docker, Docker Compose
-   **包管理**: `uv`

## 快速开始

### 环境要求

-   Docker
-   Docker Compose

### 安装与运行

1.  **克隆仓库**:
    ```bash
    git clone <your-repository-url>
    cd graphiti_project
    ```

2.  **配置环境**:
    在项目根目录创建一个 `.env` 文件。你至少需要提供你的 OpenAI API 密钥：
    ```env
    OPENAI_API_KEY=your_api_key_here
    # 其他可选的环境变量也可以在这里设置
    ```

3.  **构建并运行**:
    使用 Docker Compose 构建镜像并后台启动所有服务。

    ```bash
    docker-compose up -d --build
    ```

    `--build` 参数确保在 `Dockerfile` 或源代码发生变化时重新构建镜像。如需停止所有服务，请运行 `docker-compose down`。

### 访问服务

-   **FastAPI 应用**:
    -   API 文档 (Swagger UI): `http://localhost:8000/docs`
    -   应用主页: `http://localhost:8000`

-   **Neo4j Browser**:
    -   URL: `http://localhost:7474`
    -   用户名: `neo4j`
    -   密码: `password123` (或你在 `.env` 文件中设置的密码)

## 使用方法

1.  **数据录入**:
    访问 `http://localhost:8000/docs`，使用 `POST /api/add-text` 接口提交一段文本进行处理。

2.  **触发计算**:
    使用 `POST /api/calculate/*` 下的各个接口来对图谱数据运行 PageRank、社群发现或动量得分的计算。

3.  **查询洞察**:
    -   使用 `GET /api/hot-entities` 接口获取当前热门实体的排序列表。
    -   访问 Neo4j Browser (`http://localhost:7474`)，使用 Cypher 查询来自由探索图谱结构以及节点上已计算出的属性（`pageRank`, `communityId`, `momentum_score`）。

## 机器人资讯爬虫（Crawler）

爬虫入口为 `crawler` 子系统，负责执行“抓取 -> 清洗 -> 去重 -> 压缩 -> 入库”流程，默认按灰度模式运行（只抓取+压缩，不入库）。

### 快速命令

1.  单次全流程（默认不入库）:
    ```bash
    python -m crawler.cli run-once --since-hours 24 --max-items-per-source 20
    ```

2.  仅抓取:
    ```bash
    python -m crawler.cli crawl --since-hours 24 --source rss_36kr_newsflash
    ```

3.  仅处理压缩:
    ```bash
    python -m crawler.cli compress --process-limit 300
    ```

4.  失败重试:
    ```bash
    python -m crawler.cli retry --status ALL --process-limit 300
    ```

5.  日期回补（UTC日）:
    ```bash
    python -m crawler.cli backfill --from 2026-04-01 --to 2026-04-12
    ```

### 配置与产物

-   源配置: `crawler/config/sources.yaml`
-   流水线配置: `crawler/config/pipeline.yaml`
-   运行日志: `var/crawler/logs/crawler.log`
-   每次运行摘要: `var/crawler/runs/<run_id>.json`

当需要开启入库时，先将 `crawler/config/pipeline.yaml` 中 `gray_mode` 改为 `false`，再执行命令并加 `--ingest` 参数。
