-- ============================================================
-- 智链机器人 - 本体元数据表（inc_ 前缀）
-- 基于 V2 本体模型设计文档
-- ============================================================

CREATE DATABASE IF NOT EXISTS ontology_schema_registry 
  CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;

USE ontology_schema_registry;

-- 1. 本体模型信息表
CREATE TABLE IF NOT EXISTS inc_ontology_meta (
    id VARCHAR(64) PRIMARY KEY COMMENT '本体ID',
    ontology_name VARCHAR(128) NOT NULL COMMENT '本体名称',
    version VARCHAR(16) COMMENT '版本号',
    description TEXT COMMENT '描述',
    domain VARCHAR(64) COMMENT '领域',
    cidoc_version VARCHAR(16) COMMENT 'CIDOC CRM版本',
    architecture_type VARCHAR(32) DEFAULT 'five_layer' COMMENT '架构类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='本体模型信息表';

-- 2. 类定义表
CREATE TABLE IF NOT EXISTS inc_class (
    class_id VARCHAR(64) PRIMARY KEY COMMENT '类ID',
    class_name VARCHAR(128) NOT NULL COMMENT '类名称',
    class_name_en VARCHAR(128) COMMENT '英文名称',
    parent_class_id VARCHAR(64) COMMENT '父类ID',
    category ENUM('actor','object','event','concept','document',
                  'identifier','type','time','space') NOT NULL COMMENT '大类',
    class_level ENUM('core','support') DEFAULT 'core' COMMENT '类层级',
    cidoc_mapping VARCHAR(64) COMMENT 'CIDOC CRM映射',
    description TEXT COMMENT '类描述',
    icon VARCHAR(64) COMMENT '图标标识',
    color VARCHAR(16) COMMENT '展示颜色',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_parent_class_id (parent_class_id),
    INDEX idx_category (category),
    INDEX idx_class_level (class_level)
) COMMENT='类定义表';

-- 3. 属性定义表
CREATE TABLE IF NOT EXISTS inc_property (
    property_id VARCHAR(64) PRIMARY KEY COMMENT '属性ID',
    property_name VARCHAR(128) NOT NULL COMMENT '属性名称',
    property_name_en VARCHAR(128) COMMENT '英文名称',
    class_id VARCHAR(64) NOT NULL COMMENT '归属类',
    data_type ENUM('string','int','float','date','datetime','boolean','json','text') NOT NULL,
    property_group ENUM('reuse','scene','extend') DEFAULT 'scene' COMMENT '属性分组',
    cidoc_mapping VARCHAR(64) COMMENT 'CIDOC属性映射',
    is_required TINYINT DEFAULT 0 COMMENT '是否必填',
    is_unique TINYINT DEFAULT 0 COMMENT '是否唯一',
    default_value VARCHAR(255) COMMENT '默认值',
    constraints JSON COMMENT '值域约束',
    description TEXT COMMENT '属性描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_class_id (class_id)
) COMMENT='属性定义表';

-- 4. 关系定义表
CREATE TABLE IF NOT EXISTS inc_relation (
    relation_id VARCHAR(64) PRIMARY KEY COMMENT '关系ID',
    relation_name VARCHAR(128) NOT NULL COMMENT '关系名称',
    relation_name_en VARCHAR(128) COMMENT '英文名称',
    source_class_id VARCHAR(64) NOT NULL COMMENT '源实体类',
    target_class_id VARCHAR(64) NOT NULL COMMENT '目标实体类',
    relation_group ENUM('base_main','actor_object','classify') NOT NULL COMMENT '关系分组',
    cidoc_mapping VARCHAR(64) COMMENT 'CIDOC关系映射',
    cardinality VARCHAR(16) DEFAULT 'n:n' COMMENT '基数约束',
    description TEXT COMMENT '关系描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source_class_id (source_class_id),
    INDEX idx_target_class_id (target_class_id),
    INDEX idx_relation_group (relation_group)
) COMMENT='关系定义表';

-- 5. 实例注册表
CREATE TABLE IF NOT EXISTS inc_instance (
    instance_id VARCHAR(128) PRIMARY KEY COMMENT '实例ID',
    class_id VARCHAR(64) NOT NULL COMMENT '归属类',
    canonical_name VARCHAR(256) NOT NULL COMMENT '规范名称',
    neo4j_node_id BIGINT COMMENT 'Neo4j节点ID',
    mongodb_doc_id VARCHAR(64) COMMENT 'MongoDB文档ID',
    status ENUM('active','inactive','merged') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_class_id (class_id),
    INDEX idx_canonical_name (canonical_name),
    INDEX idx_status (status),
    INDEX idx_neo4j_node_id (neo4j_node_id)
) COMMENT='实例注册表';

-- 6. 概念分类表
CREATE TABLE IF NOT EXISTS inc_concept (
    concept_id VARCHAR(64) PRIMARY KEY COMMENT '概念ID',
    concept_name VARCHAR(128) NOT NULL COMMENT '概念名称',
    concept_type ENUM('industry_network','industry_chain','industry_node','value_link') NOT NULL,
    parent_concept_id VARCHAR(64) COMMENT '父概念ID',
    description TEXT COMMENT '描述',
    region VARCHAR(64) COMMENT '区域（产业网）',
    core_product VARCHAR(128) COMMENT '核心产品（产业链）',
    position INT COMMENT '位置序号（价值环节）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_concept_type (concept_type),
    INDEX idx_parent_concept_id (parent_concept_id)
) COMMENT='产业概念分类表';

-- 7. 公理定义表
CREATE TABLE IF NOT EXISTS inc_axiom (
    axiom_id VARCHAR(64) PRIMARY KEY COMMENT '公理ID',
    axiom_code VARCHAR(16) NOT NULL COMMENT '公理编码',
    axiom_type ENUM('basic','decision','evolution') NOT NULL COMMENT '公理类型',
    axiom_name VARCHAR(128) NOT NULL COMMENT '公理名称',
    axiom_content TEXT NOT NULL COMMENT '公理内容',
    trigger_condition TEXT COMMENT '触发条件（演化公理）',
    validation_rule TEXT COMMENT '验证规则（JSON格式）',
    priority INT DEFAULT 0 COMMENT '优先级',
    is_enabled TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_axiom_type (axiom_type),
    INDEX idx_is_enabled (is_enabled)
) COMMENT='公理定义表';
