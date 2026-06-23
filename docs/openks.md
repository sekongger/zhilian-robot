openks/
├── README.md                     # 项目说明：架构、核心能力、部署与使用规范
├── requirements.txt              # 核心依赖（PyTorch、Transformers、SPG、NetworkX、Neo4j等）
├── conf/                         # 配置中心：环境隔离 + 模型/知识库配置
│   ├── base/                     # 基础配置
│   │   ├── logger.yaml           # 日志配置
│   │   ├── storage.yaml          # 图谱存储配置（Neo4j/ArangoDB/本地文件）
│   │   └── common.yaml           # 通用常量（推理超时、融合阈值等）
│   ├── dev/                      # 开发环境配置
│   │   ├── model_config.yaml     # 模型部署配置（本地/测试环境）
│   │   └── kg_config.yaml        # 知识库构建配置（测试数据源）
│   └── prod/                     # 生产环境配置（敏感信息通过环境变量注入）
│       ├── model_config.yaml
│       └── kg_config.yaml
├── src/                          # 核心源码（扁平化结构）
│   ├── __init__.py
│   ├── model/                    # 知识计算模型组件（按能力分类）
│   │   ├── __init__.py
│   │   ├── base_model.py         # 模型抽象基类（定义推理、训练、部署接口）
│   │   ├── entity_extract/       # 实体抽取模型
│   │   │   ├── __init__.py
│   │   │   ├── llm_entity_extract.py # 大模型实体抽取（适配LLM API/本地部署）
│   │   │   ├── rule_entity_extract.py # 规则式实体抽取
│   │   │   └── ner_entity_extract.py  # 传统NER模型（BERT/ERNIE）
│   │   ├── relation_extract/     # 关系抽取模型
│   │   │   ├── __init__.py
│   │   │   ├── llm_relation_extract.py
│   │   │   └── supervised_relation_extract.py
│   │   ├── event_extract/        # 事件抽取模型
│   │   │   ├── __init__.py
│   │   │   └── llm_event_extract.py
│   │   ├── knowledge_fusion/     # 知识融合模型（实体对齐、属性融合）
│   │   │   ├── __init__.py
│   │   │   ├── entity_alignment.py # 实体对齐（相似度计算/聚类）
│   │   │   └── attribute_fusion.py # 属性融合（冲突消解）
│   │   ├── reasoning/            # 推理模型（符号/神经/混合）
│   │   │   ├── __init__.py
│   │   │   ├── symbolic_reasoning.py # 符号规则推理
│   │   │   ├── llm_reasoning.py      # 大模型逻辑推理
│   │   │   └── hybrid_reasoning.py   # 符号+神经混合推理
│   │   └── model_factory.py       # 模型工厂：按任务类型创建模型实例
│   ├── kg/                       # 分层知识库（common/fact/cognition/decision）
│   │   │   ├── __init__.py
│   │   │   ├── common/           # 通用知识库（省市、行业分类、通用概念）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── schema/       # 通用Schema定义（YAML/SPG DSL）
│   │   │   │   │   ├── region_schema.yaml # 省市Schema
│   │   │   │   │   └── industry_category_schema.yaml # 行业分类Schema
│   │   │   │   ├── builder/      # 通用知识库构建器（数据接入+标准化）
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── region_builder.py # 省市知识库构建
│   │   │   │   │   └── industry_category_builder.py
│   │   │   │   ├── solver/       # 通用知识库查询求解器
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── common_solver.py # 通用查询拆解/执行
│   │   │   │   └── reasoner/     # 通用知识库推理器
│   │   │   │       ├── __init__.py
│   │   │   │       └── common_reasoner.py # 通用规则推理（如省市从属关系）
│   │   │   ├── fact/             # 事实知识库（资讯/研报/企业+融合大图）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── news/         # 资讯知识库
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── schema/
│   │   │   │   │   │   └── news_schema.yaml # 资讯SPG Schema
│   │   │   │   │   ├── builder/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   └── news_builder.py # 资讯抽取+入库
│   │   │   │   │   ├── solver/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   └── news_solver.py # 资讯查询求解
│   │   │   │   │   └── reasoner/
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       └── news_reasoner.py # 资讯事件推理
│   │   │   │   ├── research_report/ # 研报知识库
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── schema/
│   │   │   │   │   ├── builder/
│   │   │   │   │   ├── solver/
│   │   │   │   │   └── reasoner/
│   │   │   │   ├── enterprise/   # 企业知识库
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── schema/
│   │   │   │   │   ├── builder/
│   │   │   │   │   ├── solver/
│   │   │   │   │   └── reasoner/
│   │   │   │   └── industry_network/ # 融合大图（Fact Graph）
│   │   │   │       ├── __init__.py
│   │   │   │       ├── schema/   # 大图统一Schema（对齐所有子库）
│   │   │   │       │   └── industry_network_schema.yaml
│   │   │   │       ├── builder/  # 大图构建器（核心：知识融合）
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   ├── knowledge_fusion.py # 实体/关系对齐融合
│   │   │   │       │   └── industry_network_builder.py # 大图组装
│   │   │   │       ├── solver/   # 大图查询求解器（多源联合查询）
│   │   │   │       │   ├── __init__.py
│   │   │   │       │   └── industry_network_solver.py
│   │   │   │       └── reasoner/ # 大图推理器（跨库规则推理）
│   │   │   │           ├── __init__.py
│   │   │   │           └── industry_network_reasoner.py
│   │   │   ├── cognition/        # 领域链图（产业链/创新链/资金链/人才链）
│   │   │   │   ├── __init__.py
│   │   │   │   ├── industry_chain/ # 产业链
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── ai_industry_chain/ # AI产业链子图
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── schema/
│   │   │   │   │   │   ├── builder/ # 产业链构建（基于大图+领域规则）
│   │   │   │   │   │   ├── solver/ # 产业链查询（如上下游企业）
│   │   │   │   │   │   └── reasoner/ # 产业链推理（如供需关系）
│   │   │   │   │   └── chip_industry_chain/ # 芯片产业链（预留）
│   │   │   │   ├── innovation_chain/ # 创新链
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── ai_innovation_chain/
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       ├── schema/
│   │   │   │   │       ├── builder/
│   │   │   │   │       ├── solver/
│   │   │   │   │       └── reasoner/
│   │   │   │   ├── capital_chain/ # 资金链
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── ai_capital_chain/
│   │   │   │   └── talent_chain/  # 人才链
│   │   │   │       ├── __init__.py
│   │   │   │       └── ai_talent_chain/
│   │   │   └── decision/         # 决策图谱（业务场景化决策）
│   │   │       ├── __init__.py
│   │   │       ├── ai_investment_decision/ # AI投资决策图谱
│   │   │       │   ├── __init__.py
│   │   │       │   ├── schema/
│   │   │       │   ├── builder/  # 决策图谱构建（基于链图+业务规则）
│   │   │       │   ├── solver/   # 决策查询（如投资标的筛选）
│   │   │       │   └── reasoner/ # 决策推理（如风险评估）
│   │   │       └── ai_policy_decision/ # AI政策决策图谱（预留）
│   │   ├── common/               # 知识库通用工具
│   │   │   ├── __init__.py
│   │   │   ├── kg_client.py      # 图谱存储客户端（统一对接Neo4j/ArangoDB）
│   │   │   ├── schema_parser.py  # Schema解析器（SPG DSL/YAML转结构化）
│   │   │   └── kg_metrics.py     # 知识库指标（实体数、关系数、融合率）
│   │   └── server/               # 对外服务层（对接智能体/前端）
│   │       ├── __init__.py
│   │       ├── base_server.py    # 服务抽象基类（HTTP/GRPC）
│   │       ├── http_server.py    # HTTP接口（RESTful）
│   │       └── skill_adapter.py  # 智能体Skill适配（MCP/Function Call）
│   └── metrics/                  # 全局监控指标
│       ├── __init__.py
│       ├── model_metrics.py      # 模型指标（抽取准确率、推理召回率）
│       └── kg_metrics.py         # 知识库指标（构建成功率、融合率）
├── tests/                        # 测试目录
│   ├── __init__.py
│   ├── test_model/               # 模型测试
│   │   ├── test_entity_extract.py
│   │   └── test_knowledge_fusion.py
│   └── test_kg/                  # 知识库测试
│       ├── test_fact_kg.py
│       ├── test_industry_network.py
│       └── test_ai_industry_chain.py
├── scripts/                      # 辅助脚本
│   ├── deploy.sh                 # 部署脚本
│   ├── init_kg.sh                # 知识库初始化
│   └── model_deploy.sh           # 模型部署脚本
└── docs/                         # 文档
    ├── architecture.md          # 架构设计文档
    ├── model_docs.md            # 模型能力说明
    ├── kg_docs.md               # 知识库分层与构建流程
    └── api_docs.md              # 对外接口文档