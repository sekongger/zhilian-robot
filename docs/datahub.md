datahub/
├── README.md                     # 项目说明：架构、部署、核心功能、开发规范
├── requirements.txt              # 核心依赖清单（pandas、pyspark、requests、PyYAML等）
├── conf/                         # 配置中心：环境隔离 + 通用配置（无Schema）
│   ├── base/                     # 基础配置（通用参数）
│   │   ├── logger.yaml           # 日志配置
│   │   ├── storage.yaml          # 存储配置（HDFS/本地/OSS路径）
│   │   └── common.yaml           # 通用常量（超时时间、数据格式）
│   ├── dev/                      # 开发环境配置
│   │   ├── data_loader.yaml      # 数据源配置（测试爬虫/RSS地址）
│   │   └── pipeline.yaml         # 调度配置（开发环境）
│   └── prod/                     # 生产环境配置（敏感信息通过环境变量注入）
│       ├── data_loader.yaml
│       └── pipeline.yaml
├── src/                          # 核心源码（扁平化）
│   ├── __init__.py
│   ├── data_loader/              # 多源数据接入组件
│   │   ├── __init__.py
│   │   ├── base_loader.py        # 抽象基类：定义接入接口
│   │   ├── crawler_loader.py     # 爬虫数据源
│   │   ├── rss_loader.py         # RSS订阅源
│   │   ├── file_loader.py        # 文件源（CSV/Excel/JSON）
│   │   ├── api_loader.py         # API源（第三方接口）
│   │   └── loader_factory.py     # 工厂模式：创建Loader实例
│   ├── operators/                # 数据治理算子
│   │   ├── __init__.py
│   │   ├── base_operator.py      # 算子抽象基类
│   │   ├── clean_ops/            # 清洗算子
│   │   │   ├── __init__.py
│   │   │   ├── null_clean.py     # 空值处理
│   │   │   └── format_clean.py   # 格式清洗
│   │   ├── dedup_ops/            # 去重算子
│   │   │   ├── __init__.py
│   │   │   ├── exact_dedup.py    # 精准去重
│   │   │   └── fuzzy_dedup.py    # 模糊去重
│   │   ├── standard_ops/         # 标准化算子
│   │   │   ├── __init__.py
│   │   │   ├── entity_standard.py # 实体标准化
│   │   │   └── field_standard.py # 字段标准化
│   │   └── filter_ops/           # 过滤算子（预留）
│   │       ├── __init__.py
│   │       └── condition_filter.py
│   ├── pipeline/                 # 数据加工流水线（模板+业务包+调度）
│   │   ├── __init__.py
│   │   ├── template/             # 流水线模板层（含Schema基础模板）
│   │   │   ├── __init__.py
│   │   │   ├── base_pipeline.py  # 流水线抽象基类（编排、执行、监控）
│   │   │   ├── pipeline_mixin.py # 通用混入类（日志、配置加载、指标）
│   │   │   ├── base_scheduler.py # 调度抽象类（统一查询接口）
│   │   │   └── base_schema.yaml  # Schema基础模板（通用规则）
│   │   ├── news_pipeline/        # 资讯库流水线包（含专属Schema）
│   │   │   ├── __init__.py
│   │   │   ├── news_schema.yaml  # 资讯专属Schema
│   │   │   ├── news_process.py   # 资讯加工流程（编排Loader+Operators）
│   │   │   └── news_scheduler.py # 资讯调度配置（对接Dobin）
│   │   ├── company_pipeline/     # 企业库流水线包
│   │   │   ├── __init__.py
│   │   │   ├── company_schema.yaml# 企业专属Schema
│   │   │   ├── company_process.py # 企业加工流程
│   │   │   └── company_scheduler.py # 企业调度配置
│   │   ├── patent_pipeline/      # 专利库流水线包
│   │   │   ├── __init__.py
│   │   │   ├── patent_schema.yaml   # 专利专属Schema
│   │   │   ├── patent_process.py # 专利加工流程
│   │   │   └── patent_scheduler.py # 专利调度配置
│   ├── common/                   # 通用工具
│   │   ├── __init__.py
│   │   ├── logger.py             # 日志工具
│   │   ├── storage.py            # 存储工具
│   │   ├── validator.py          # 数据校验工具（调用Schema加载器+校验规则）
│   │   └── schema_loader.py      # Schema加载工具（读取YAML模板）
│   └── metrics/                  # 监控指标（前端展示用）
│       ├── __init__.py
│       ├── data_metrics.py       # 数据指标（各库数据量、更新频率）
│       └── pipeline_metrics.py   # 流水线指标（执行成功率、耗时）
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_data_loader/         # 接入组件测试
│   ├── test_operators/           # 算子测试
│   ├── test_common/              # 通用工具测试
│   │   ├── __init__.py
│   │   └── test_validator.py
│   └── test_pipeline/            # 流水线测试
│       ├── __init__.py
│       ├── test_template/
│       │   ├── test_base_pipeline.py
│       │   └── test_schema_loader.py
│       ├── test_news_pipeline/
│       │   ├── test_news_schema.py
│       │   └── test_news_process.py
│       ├── test_company_pipeline/
│       └── test_patent_pipeline/
├── scripts/                      # 辅助脚本
│   ├── deploy.sh                 # 部署脚本
│   ├── init_schema.sh            # 初始化Schema（加载各业务Schema到存储）
│   └── sync_config.sh            # 配置同步脚本
└── docs/                         # 文档
    ├── architecture.md          # 架构设计文档
    ├── api_docs.md               # 接口文档
    ├── schema_docs.md            # Schema模板说明文档
    └── user_guide.md            # 使用手册