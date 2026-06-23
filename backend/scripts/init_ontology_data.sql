-- ============================================================
-- 智链机器人 - 本体元数据初始化数据
-- 基于 V2 本体模型设计文档
-- ============================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE ontology_schema_registry;

-- 插入本体模型信息
INSERT INTO inc_ontology_meta (id, ontology_name, version, description, domain, cidoc_version, architecture_type)
VALUES ('ONT_ROBOT_CHAIN', '机器人产业链本体', '2.0.0', '基于CIDOC CRM的机器人产业链知识图谱本体模型', '机器人产业', '7.3.1', 'five_layer')
ON DUPLICATE KEY UPDATE version = VALUES(version), updated_at = NOW();

-- 插入五大核心类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, cidoc_mapping, description, color) VALUES
('CLS_CONCEPT', '产业概念类', 'Industrial Concept', 'concept', 'core', 'E28_Conceptual_Object', '产业网链的抽象结构与分类属性', '#9C27B0'),
('CLS_ACTOR', '产业主体类', 'Industrial Actor', 'actor', 'core', 'E39_Actor', '参与产业网链活动的异质性角色', '#2196F3'),
('CLS_OBJECT', '产业对象类', 'Industrial Object', 'object', 'core', 'E70_Thing', '支撑产业网链运行的资源与规则', '#4CAF50'),
('CLS_EVENT', '产业事件类', 'Industrial Event', 'event', 'core', 'E5_Event', '记录主体与对象的动态交互', '#FF9800'),
('CLS_DOCUMENT', '产业文档类', 'Industrial Document', 'document', 'core', 'E31_Document', '记录实体与事件的凭证性文档', '#607D8B')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入四大支撑类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, cidoc_mapping, description, color) VALUES
('CLS_IDENTIFIER', '标识要素', 'Identifier Element', 'identifier', 'support', 'E41_Appellation', '实体的唯一标识与编码', '#795548'),
('CLS_TYPE', '类型要素', 'Type Element', 'type', 'support', 'E55_Type', '实体的分类与层级', '#9E9E9E'),
('CLS_TIME', '时间要素', 'Time Element', 'time', 'support', 'E52_Time-Span', '事件与状态的时间维度', '#00BCD4'),
('CLS_SPACE', '空间要素', 'Space Element', 'space', 'support', 'E53_Place', '实体与事件的空间维度', '#8BC34A')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入核心类子类 - 产业概念子类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, parent_class_id, cidoc_mapping, description, color) VALUES
('CLS_INDUSTRY_NETWORK', '产业网', 'Industry Network', 'concept', 'core', 'CLS_CONCEPT', 'E28_Conceptual_Object', '区域/领域内产业节点的网状聚合结构（基底）', '#9C27B0'),
('CLS_INDUSTRY_CHAIN', '产业链', 'Industry Chain', 'concept', 'core', 'CLS_CONCEPT', 'E28_Conceptual_Object', '围绕核心产品的价值传递线性结构（主线）', '#7B1FA2'),
('CLS_INDUSTRY_NODE', '产业节点', 'Industry Node', 'concept', 'core', 'CLS_CONCEPT', 'E28_Conceptual_Object', '产业网与产业链的交汇点', '#6A1B9A'),
('CLS_VALUE_LINK', '产业价值环节', 'Value Link', 'concept', 'core', 'CLS_CONCEPT', 'E28_Conceptual_Object', '产业链上的价值创造单元', '#4A148C')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入核心类子类 - 产业主体子类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, parent_class_id, cidoc_mapping, description, color) VALUES
('CLS_ENTERPRISE', '企业', 'Enterprise', 'actor', 'core', 'CLS_ACTOR', 'E39_Actor', '企业法人主体', '#1976D2'),
('CLS_RESEARCH_INST', '科研机构', 'Research Institution', 'actor', 'core', 'CLS_ACTOR', 'E39_Actor', '高校/研究院所', '#1565C0'),
('CLS_GOVERNMENT', '政府', 'Government', 'actor', 'core', 'CLS_ACTOR', 'E39_Actor', '政府部门', '#0D47A1'),
('CLS_FINANCIAL_INST', '金融机构', 'Financial Institution', 'actor', 'core', 'CLS_ACTOR', 'E39_Actor', '银行/基金/投资机构', '#0277BD'),
('CLS_PERSON', '人物', 'Person', 'actor', 'core', 'CLS_ACTOR', 'E21_Person', '自然人主体', '#039BE5')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入核心类子类 - 产业对象子类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, parent_class_id, cidoc_mapping, description, color) VALUES
('CLS_PRODUCT', '产品', 'Product', 'object', 'core', 'CLS_OBJECT', 'E70_Thing', '物质对象-产品', '#388E3C'),
('CLS_TECHNOLOGY', '技术', 'Technology', 'object', 'core', 'CLS_OBJECT', 'E70_Thing', '技术对象-专利/技术', '#2E7D32'),
('CLS_CAPITAL', '资金', 'Capital', 'object', 'core', 'CLS_OBJECT', 'E70_Thing', '资金对象', '#1B5E20'),
('CLS_STANDARD', '标准', 'Standard', 'object', 'core', 'CLS_OBJECT', 'E70_Thing', '行业标准/规范', '#43A047')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入核心类子类 - 产业事件子类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, parent_class_id, cidoc_mapping, description, color) VALUES
('CLS_INVESTMENT_EVENT', '投资事件', 'Investment Event', 'event', 'core', 'CLS_EVENT', 'E5_Event', '融资/投资事件', '#F57C00'),
('CLS_COOPERATION_EVENT', '合作事件', 'Cooperation Event', 'event', 'core', 'CLS_EVENT', 'E5_Event', '合作/签约事件', '#EF6C00'),
('CLS_PRODUCT_EVENT', '产品事件', 'Product Event', 'event', 'core', 'CLS_EVENT', 'E5_Event', '产品发布/上市事件', '#E65100'),
('CLS_POLICY_EVENT', '政策事件', 'Policy Event', 'event', 'core', 'CLS_EVENT', 'E5_Event', '政策发布/实施事件', '#FF8F00')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入核心类子类 - 产业文档子类
INSERT INTO inc_class (class_id, class_name, class_name_en, category, class_level, parent_class_id, cidoc_mapping, description, color) VALUES
('CLS_NEWS_DOC', '资讯文档', 'News Document', 'document', 'core', 'CLS_DOCUMENT', 'E31_Document', '新闻资讯类文档', '#546E7A'),
('CLS_POLICY_DOC', '政策文档', 'Policy Document', 'document', 'core', 'CLS_DOCUMENT', 'E32_Authority_Document', '政府政策类文档', '#455A64'),
('CLS_RESEARCH_DOC', '研报文档', 'Research Document', 'document', 'core', 'CLS_DOCUMENT', 'E31_Document', '研究报告类文档', '#37474F'),
('CLS_PATENT_DOC', '专利文档', 'Patent Document', 'document', 'core', 'CLS_DOCUMENT', 'E31_Document', '专利技术类文档', '#263238')
ON DUPLICATE KEY UPDATE class_name = VALUES(class_name), updated_at = NOW();

-- 插入基础约束公理
INSERT INTO inc_axiom (axiom_id, axiom_code, axiom_type, axiom_name, axiom_content, priority) VALUES
('AX_A1', 'A1', 'basic', '结构完整性约束', '产业网链必须包含1个产业网和≥1条产业链', 0),
('AX_A2', 'A2', 'basic', '类型唯一性约束', '产业节点与细分类型一一对应', 0),
('AX_A3', 'A3', 'basic', '主体归属约束', '产业主体必须聚集于≥1个产业节点', 0),
('AX_A4', 'A4', 'basic', '链条完整性约束', '产业链必须包含≥2个价值环节', 0),
('AX_A5', 'A5', 'basic', '可信溯源约束', '所有事实性陈述必须绑定文档来源与情境约束', 0)
ON DUPLICATE KEY UPDATE axiom_name = VALUES(axiom_name);

-- 插入决策场景公理
INSERT INTO inc_axiom (axiom_id, axiom_code, axiom_type, axiom_name, axiom_content, priority) VALUES
('AX_D1', 'D1', 'decision', '招商引资决策', '基于产业节点聚集度和价值环节缺口分析，推荐招商目标企业', 1),
('AX_D2', 'D2', 'decision', '供应链风险评估', '基于供应关系链路分析，识别关键供应商和潜在风险点', 1),
('AX_D3', 'D3', 'decision', '技术路线规划', '基于技术关联和专利布局，规划技术发展路径', 1)
ON DUPLICATE KEY UPDATE axiom_name = VALUES(axiom_name);

-- 插入演化适配公理
INSERT INTO inc_axiom (axiom_id, axiom_code, axiom_type, axiom_name, axiom_content, priority) VALUES
('AX_E1', 'E1', 'evolution', '实体合并规则', '当两个实体被识别为同一实体时，合并其属性和关系', 2),
('AX_E2', 'E2', 'evolution', '关系推理规则', '基于已有关系推理隐含关系（如A投资B，B投资C，则A间接投资C）', 2),
('AX_E3', 'E3', 'evolution', '时效性更新规则', '当新文档提供更新信息时，更新实体属性并保留历史版本', 2)
ON DUPLICATE KEY UPDATE axiom_name = VALUES(axiom_name);

-- 插入关系定义 - 基底-主线赋能关系
INSERT INTO inc_relation (relation_id, relation_name, relation_name_en, source_class_id, target_class_id, relation_group, cidoc_mapping, description) VALUES
('REL_SUPPORTS_CHAIN', '支撑产业链', 'Supports Chain', 'CLS_INDUSTRY_NETWORK', 'CLS_INDUSTRY_CHAIN', 'base_main', 'P15_was_influenced_by', '产业网的资源要素支撑产业链价值传导'),
('REL_FEEDS_BACK', '反哺产业网', 'Feeds Back to Network', 'CLS_INDUSTRY_CHAIN', 'CLS_INDUSTRY_NETWORK', 'base_main', 'P15i_influenced', '产业链优化需求推动产业网要素配置升级'),
('REL_CONTAINS_NODE', '包含节点', 'Contains Node', 'CLS_INDUSTRY_NETWORK', 'CLS_INDUSTRY_NODE', 'base_main', 'P89_falls_within', '产业网包含产业节点'),
('REL_RELIES_ON_NODE', '依托节点', 'Relies On Node', 'CLS_INDUSTRY_CHAIN', 'CLS_INDUSTRY_NODE', 'base_main', 'P9_consists_of', '产业链依托产业节点'),
('REL_TRANSMITS_VALUE', '价值传递', 'Transmits Value To', 'CLS_VALUE_LINK', 'CLS_VALUE_LINK', 'base_main', 'P134_continued', '价值环节间价值传递')
ON DUPLICATE KEY UPDATE relation_name = VALUES(relation_name);

-- 插入关系定义 - 主体-对象关系
INSERT INTO inc_relation (relation_id, relation_name, relation_name_en, source_class_id, target_class_id, relation_group, cidoc_mapping, description) VALUES
('REL_INVEST', '投资', 'Invest', 'CLS_ACTOR', 'CLS_ACTOR', 'actor_object', 'P11_had_participant', '投资关系'),
('REL_SUPPLY', '供应', 'Supply', 'CLS_ENTERPRISE', 'CLS_ENTERPRISE', 'actor_object', 'P16_used_specific_object', '供应关系'),
('REL_COMPETE', '竞争', 'Compete', 'CLS_ENTERPRISE', 'CLS_ENTERPRISE', 'actor_object', NULL, '竞争关系'),
('REL_COOPERATE', '合作', 'Cooperate', 'CLS_ACTOR', 'CLS_ACTOR', 'actor_object', 'P11_had_participant', '合作关系'),
('REL_PRODUCE', '生产', 'Produce', 'CLS_ENTERPRISE', 'CLS_PRODUCT', 'actor_object', 'P108_has_produced', '生产关系'),
('REL_USE_TECH', '应用技术', 'Use Technology', 'CLS_ENTERPRISE', 'CLS_TECHNOLOGY', 'actor_object', 'P16_used_specific_object', '应用技术'),
('REL_OWN_PATENT', '拥有专利', 'Own Patent', 'CLS_ACTOR', 'CLS_PATENT_DOC', 'actor_object', 'P105_right_held_by', '专利所有权'),
('REL_PARTICIPATE', '参与事件', 'Participate In', 'CLS_ACTOR', 'CLS_EVENT', 'actor_object', 'P11_had_participant', '主体参与事件')
ON DUPLICATE KEY UPDATE relation_name = VALUES(relation_name);

-- 插入关系定义 - 分类归属关系
INSERT INTO inc_relation (relation_id, relation_name, relation_name_en, source_class_id, target_class_id, relation_group, cidoc_mapping, description) VALUES
('REL_BELONG_TO_NODE', '归属节点', 'Belong To Node', 'CLS_ACTOR', 'CLS_INDUSTRY_NODE', 'classify', 'P89_falls_within', '主体归属产业节点'),
('REL_BELONG_TO_CHAIN', '归属产业链', 'Belong To Chain', 'CLS_ACTOR', 'CLS_INDUSTRY_CHAIN', 'classify', 'P89_falls_within', '主体归属产业链'),
('REL_HAS_TYPE', '具有类型', 'Has Type', 'CLS_ACTOR', 'CLS_TYPE', 'classify', 'P2_has_type', '实体类型关联'),
('REL_MENTION', '文档提及', 'Mention', 'CLS_DOCUMENT', 'CLS_ACTOR', 'classify', 'P67_refers_to', '文档提及实体'),
('REL_LOCATED_IN', '位于', 'Located In', 'CLS_ACTOR', 'CLS_SPACE', 'classify', 'P53_has_former_or_current_location', '实体地理位置'),
('REL_OCCURRED_AT', '发生于', 'Occurred At', 'CLS_EVENT', 'CLS_TIME', 'classify', 'P4_has_time-span', '事件发生时间')
ON DUPLICATE KEY UPDATE relation_name = VALUES(relation_name);

-- 插入属性定义 - 企业属性
INSERT INTO inc_property (property_id, property_name, property_name_en, class_id, data_type, property_group, is_required, description) VALUES
('PROP_ENT_NAME', '企业名称', 'Enterprise Name', 'CLS_ENTERPRISE', 'string', 'reuse', 1, '企业全称'),
('PROP_ENT_CODE', '统一社会信用代码', 'Unified Social Credit Code', 'CLS_ENTERPRISE', 'string', 'reuse', 0, '18位统一社会信用代码'),
('PROP_ENT_REG_CAPITAL', '注册资本', 'Registered Capital', 'CLS_ENTERPRISE', 'float', 'scene', 0, '注册资本（万元）'),
('PROP_ENT_ESTABLISH_DATE', '成立日期', 'Establish Date', 'CLS_ENTERPRISE', 'date', 'scene', 0, '企业成立日期'),
('PROP_ENT_INDUSTRY', '所属行业', 'Industry', 'CLS_ENTERPRISE', 'string', 'scene', 0, '所属行业分类'),
('PROP_ENT_ADDRESS', '注册地址', 'Address', 'CLS_ENTERPRISE', 'string', 'scene', 0, '企业注册地址'),
('PROP_ENT_LEGAL_REP', '法定代表人', 'Legal Representative', 'CLS_ENTERPRISE', 'string', 'scene', 0, '法定代表人姓名'),
('PROP_ENT_STATUS', '经营状态', 'Business Status', 'CLS_ENTERPRISE', 'string', 'scene', 0, '经营状态（存续/注销等）')
ON DUPLICATE KEY UPDATE property_name = VALUES(property_name);

-- 插入属性定义 - 产品属性
INSERT INTO inc_property (property_id, property_name, property_name_en, class_id, data_type, property_group, is_required, description) VALUES
('PROP_PROD_NAME', '产品名称', 'Product Name', 'CLS_PRODUCT', 'string', 'reuse', 1, '产品名称'),
('PROP_PROD_CATEGORY', '产品类别', 'Product Category', 'CLS_PRODUCT', 'string', 'scene', 0, '产品分类'),
('PROP_PROD_SPEC', '产品规格', 'Product Specification', 'CLS_PRODUCT', 'text', 'scene', 0, '产品规格参数'),
('PROP_PROD_PRICE', '产品价格', 'Product Price', 'CLS_PRODUCT', 'float', 'scene', 0, '产品价格（元）')
ON DUPLICATE KEY UPDATE property_name = VALUES(property_name);

-- 插入属性定义 - 技术属性
INSERT INTO inc_property (property_id, property_name, property_name_en, class_id, data_type, property_group, is_required, description) VALUES
('PROP_TECH_NAME', '技术名称', 'Technology Name', 'CLS_TECHNOLOGY', 'string', 'reuse', 1, '技术名称'),
('PROP_TECH_DOMAIN', '技术领域', 'Technology Domain', 'CLS_TECHNOLOGY', 'string', 'scene', 0, '技术所属领域'),
('PROP_TECH_MATURITY', '技术成熟度', 'Technology Maturity', 'CLS_TECHNOLOGY', 'string', 'scene', 0, '技术成熟度等级'),
('PROP_TECH_DESC', '技术描述', 'Technology Description', 'CLS_TECHNOLOGY', 'text', 'extend', 0, '技术详细描述')
ON DUPLICATE KEY UPDATE property_name = VALUES(property_name);

-- 插入属性定义 - 文档属性
INSERT INTO inc_property (property_id, property_name, property_name_en, class_id, data_type, property_group, is_required, description) VALUES
('PROP_DOC_TITLE', '文档标题', 'Document Title', 'CLS_DOCUMENT', 'string', 'reuse', 1, '文档标题'),
('PROP_DOC_SOURCE', '文档来源', 'Document Source', 'CLS_DOCUMENT', 'string', 'reuse', 0, '文档来源'),
('PROP_DOC_URL', '文档链接', 'Document URL', 'CLS_DOCUMENT', 'string', 'reuse', 0, '文档原始链接'),
('PROP_DOC_PUBLISH_DATE', '发布日期', 'Publish Date', 'CLS_DOCUMENT', 'datetime', 'scene', 0, '文档发布日期'),
('PROP_DOC_CONTENT', '文档内容', 'Document Content', 'CLS_DOCUMENT', 'text', 'extend', 0, '文档正文内容')
ON DUPLICATE KEY UPDATE property_name = VALUES(property_name);

-- 插入产业概念示例数据
INSERT INTO inc_concept (concept_id, concept_name, concept_type, description, region) VALUES
('CON_ROBOT_NETWORK', '机器人产业网', 'industry_network', '中国机器人产业网络', '中国'),
('CON_YANGTZE_ROBOT', '长三角机器人产业网', 'industry_network', '长三角地区机器人产业集群', '长三角')
ON DUPLICATE KEY UPDATE concept_name = VALUES(concept_name);

INSERT INTO inc_concept (concept_id, concept_name, concept_type, parent_concept_id, description, core_product) VALUES
('CON_INDUSTRIAL_ROBOT_CHAIN', '工业机器人产业链', 'industry_chain', 'CON_ROBOT_NETWORK', '工业机器人全产业链', '工业机器人'),
('CON_SERVICE_ROBOT_CHAIN', '服务机器人产业链', 'industry_chain', 'CON_ROBOT_NETWORK', '服务机器人全产业链', '服务机器人'),
('CON_HUMANOID_ROBOT_CHAIN', '人形机器人产业链', 'industry_chain', 'CON_ROBOT_NETWORK', '人形机器人全产业链', '人形机器人')
ON DUPLICATE KEY UPDATE concept_name = VALUES(concept_name);

INSERT INTO inc_concept (concept_id, concept_name, concept_type, parent_concept_id, description, position) VALUES
('CON_UPSTREAM', '上游核心零部件', 'value_link', 'CON_INDUSTRIAL_ROBOT_CHAIN', '减速器、伺服电机、控制器等', 1),
('CON_MIDSTREAM', '中游本体制造', 'value_link', 'CON_INDUSTRIAL_ROBOT_CHAIN', '机器人本体设计与制造', 2),
('CON_DOWNSTREAM', '下游系统集成', 'value_link', 'CON_INDUSTRIAL_ROBOT_CHAIN', '系统集成与行业应用', 3)
ON DUPLICATE KEY UPDATE concept_name = VALUES(concept_name);
