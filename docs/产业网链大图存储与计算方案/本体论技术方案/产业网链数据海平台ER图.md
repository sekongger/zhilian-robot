# 产业网链数据海平台 ER 图

> 本文档使用 Mermaid erDiagram 语法描述平台各层表间关系，可在支持 Mermaid 的 Markdown 编辑器中渲染。

---

## 1. 数据资源层 ER 图

```mermaid
erDiagram
    %% ===== 数据资源层 =====

    Ds_Basic_Info {
        string ds_id PK "数据源ID"
        string name "数据源名称"
        string description "描述"
        float credibility_score "可信度评分"
        string ds_type "类型:INTERNET/FILE/API"
        string data_category "数据分类"
        string ds_source "来源地址"
        string responsible_person "负责人"
        boolean is_valid "是否有效"
        datetime create_time "创建时间"
        datetime update_time "更新时间"
    }

    Ds_Access_Task {
        string task_id PK "任务ID"
        string ds_id FK "数据源ID"
        string task_name "任务名称"
        string access_mode "接入模式:FULL/INCREMENT"
        int priority "优先级"
        string schedule_config "调度配置"
        json access_params "接入参数"
        json storage_config "存储配置"
        boolean is_valid "是否有效"
        datetime create_time "创建时间"
    }

    Ds_Access_Record {
        string record_id PK "执行记录ID"
        string task_id FK "任务ID"
        string ds_id FK "数据源ID"
        string exec_status "执行状态"
        int total_count "总数"
        int valid_count "有效数"
        int invalid_count "无效数"
        datetime start_time "开始时间"
        datetime end_time "结束时间"
        int exec_time "执行时长(秒)"
        string error_msg "错误信息"
    }

    Inc_Data_Type_Dict {
        string type_code PK "类型编码"
        string type_name "类型名称"
        string type_name_en "英文名"
        string parent_code FK "父类型编码"
        string icon "图标"
        string color "颜色"
        int sort_order "排序"
        string status "状态"
    }

    Minio_File_Index {
        string file_id PK "文件ID(SHA-256)"
        string content_hash "内容哈希"
        string ds_id FK "数据源ID"
        string task_id FK "任务ID"
        string record_id FK "执行记录ID"
        string file_name "文件名"
        string file_type "文件类型"
        string minio_bucket "存储桶"
        string minio_path "存储路径"
        int file_size "文件大小"
        string storage_policy "存储策略"
        datetime upload_time "上传时间"
    }

    Resource_Document {
        string resource_doc_id PK "原始文档ID"
        string resource_type FK "资源类型"
        string data_source "数据来源"
        string ds_id FK "数据源ID"
        string process_batch_id "加工批次ID"
        string status "状态"
        string title_raw "原始标题"
        text raw_content "原始内容"
        string url "来源URL"
        string resource_file_id FK "文件ID"
        datetime crawl_time "采集时间"
        datetime publish_time "发布时间"
    }

    %% 数据资源层关系
    Ds_Basic_Info ||--o{ Ds_Access_Task : "配置"
    Ds_Access_Task ||--o{ Ds_Access_Record : "产生"
    Ds_Basic_Info ||--o{ Ds_Access_Record : "关联"
    Ds_Basic_Info ||--o{ Minio_File_Index : "来源于"
    Ds_Access_Task ||--o{ Minio_File_Index : "采集"
    Ds_Access_Record ||--o{ Minio_File_Index : "记录"
    Ds_Basic_Info ||--o{ Resource_Document : "来源于"
    Minio_File_Index ||--o| Resource_Document : "关联文件"
    Inc_Data_Type_Dict ||--o{ Resource_Document : "分类"
    Inc_Data_Type_Dict ||--o| Inc_Data_Type_Dict : "父子层级"
```

---

## 2. 本体模型 ER 图

```mermaid
erDiagram
    %% ===== 本体模型（规范层） =====

    Inc_Ontology_Classes {
        string id PK "本体类ID(OC开头)"
        string name "类名称"
        string name_en "英文名"
        text description "描述"
        string parent_class_id FK "父类ID"
        enum entity_category "五维分类"
        enum layer "分层级别"
        enum status "状态"
        int version "版本号"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    Inc_Property_Definitions {
        string id PK "属性ID(PD开头)"
        string name "属性名称"
        string name_en "英文名"
        text description "描述"
        string domain_class_id FK "所属类ID"
        enum range_type "值类型"
        string range_class_id FK "目标类ID"
        boolean is_multi_valued "是否多值"
        boolean is_required "是否必填"
        boolean is_unique "是否唯一"
        string unit "计量单位"
        text validation_rule "校验规则"
        enum status "状态"
        int version "版本号"
    }

    Inc_Relation_Types {
        string id PK "关系ID(RT开头)"
        string name "关系名称"
        string name_en "英文名"
        text description "描述"
        string source_class_id FK "主体类ID"
        string target_class_id FK "客体类ID"
        string inverse_relation_id FK "逆关系ID"
        enum cardinality "基数约束"
        boolean is_symmetric "是否对称"
        boolean is_transitive "是否传递"
        enum validation_phase "校验时机"
        enum status "状态"
        int version "版本号"
    }

    Inc_Ontology_Activities {
        string id PK "动作ID"
        string name "动作名称"
        enum constraint_type "约束类型"
        string target_class_id FK "目标类ID"
        string target_property_id FK "目标属性ID"
        text expression "动作表达式"
        enum status "状态"
        int version "版本号"
    }

    Inc_Ontology_Versions {
        string id PK "版本ID"
        string version_code UK "版本号"
        text description "版本说明"
        datetime released_at "发布时间"
        string previous_version_id FK "前序版本ID"
        text change_summary "变更摘要"
        enum status "状态"
    }

    %% 本体模型关系
    Inc_Ontology_Classes ||--o| Inc_Ontology_Classes : "继承"
    Inc_Ontology_Classes ||--o{ Inc_Property_Definitions : "定义属性"
    Inc_Ontology_Classes ||--o{ Inc_Relation_Types : "作为主体"
    Inc_Ontology_Classes ||--o{ Inc_Relation_Types : "作为客体"
    Inc_Property_Definitions ||--o| Inc_Ontology_Classes : "引用目标类"
    Inc_Relation_Types ||--o| Inc_Relation_Types : "逆关系"
    Inc_Ontology_Classes ||--o{ Inc_Ontology_Activities : "约束"
    Inc_Property_Definitions ||--o{ Inc_Ontology_Activities : "约束"
    Inc_Ontology_Versions ||--o| Inc_Ontology_Versions : "版本链"
```

---

## 3. 知识网络 ER 图（5大核心）

```mermaid
erDiagram
    %% ===== 知识网络（实例层） =====

    Micro_Document {
        string micro_document_id PK "微文档ID(MC开头)"
        string doc_id FK "文档ID(资源层标准文档)"
        enum content_type "内容类型"
        text content "内容"
        json source_position "位置信息"
        string ontology_property_id FK "属性ID"
        array embedding "向量嵌入"
        string model_version "模型版本"
        float confidence "置信度"
        enum status "状态"
        string process_batch_id "加工批次ID"
        datetime created_at "创建时间"
    }

    Entity {
        string entity_id PK "实体ID(EN开头)"
        string class_id FK "本体类ID"
        enum entity_category "五维分类"
        string name "实体名称"
        string name_en "英文名"
        int version "版本号"
        string previous_version_id FK "前序版本ID"
        string change_reason "变更原因"
        enum status "状态"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    Entity_Aliases {
        bigint id PK "主键ID"
        string entity_id FK "实体ID"
        string alias "别名"
        enum alias_type "别名类型"
        float confidence "置信度"
        string source_id FK "来源Statement ID"
        datetime created_at "创建时间"
    }

    Entity_Core_Properties {
        bigint id PK "主键ID"
        string entity_id FK "实体ID"
        string property_id FK "属性定义ID"
        text property_value "属性值"
        enum value_type "值类型"
        boolean ontology_validated "已校验"
        text validation_errors "校验错误"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    Context {
        string context_id PK "上下文ID(KC开头)"
        enum context_type "类型"
        datetime begin_time "开始时间"
        datetime end_time "结束时间"
        enum time_type "时间类型"
        string doc_id FK "文档ID"
        string micro_document_id FK "微文档ID"
        text evidence_text "证据原文"
        enum extraction_method "抽取方式"
        string extraction_model "抽取模型"
        string source_agent "信息来源主体"
        string point_of_view "视角"
        json extra_context "扩展上下文"
        datetime created_at "创建时间"
    }


    Statement {
        string statement_id PK "Statement ID(ST开头)"
        string statement_hash UK "幂等哈希"
        enum statement_type "语句类型"
        string subject_id FK "主体实体ID"
        string predicate_id FK "属性/关系ID"
        enum object_type "客体类型"
        string object_class_id FK "客体本体类ID"
        string object_entity_id FK "客体实体ID"
        text object_value "客体字面量"
        enum object_value_type "字面量类型"
        string context_id FK "上下文ID"
        float confidence "置信度"
        boolean crystallized "结晶标识"
        int version "版本号"
        string previous_version_id FK "前序版本ID"
        enum status "状态"
        string process_batch_id "加工批次ID"
        datetime created_at "创建时间"
    }

    Confidence_Rules {
        string rule_id PK "规则ID"
        string rule_name "规则名称"
        enum rule_type "规则类型"
        text rule_expression "规则表达式"
        enum status "状态"
        int version "版本号"
    }

    %% 知识网络核心关系
    Micro_Document ||--o{ Context : "作为证据来源"

    Entity ||--o{ Entity_Aliases : "拥有别名"
    Entity ||--o{ Entity_Core_Properties : "拥有属性"
    Entity ||--o| Entity : "版本链"

    Entity ||--o{ Statement : "作为主体"
    Entity ||--o{ Statement : "作为客体"
    Statement ||--|| Context : "关联上下文"
    Statement ||--o| Statement : "版本链"

    Inc_Ontology_Classes ||--o{ Entity : "实例化"
    Inc_Property_Definitions ||--o{ Entity_Core_Properties : "定义"
    Inc_Property_Definitions ||--o{ Micro_Document : "关联属性"
    Inc_Property_Definitions ||--o{ Statement : "作为谓词(属性)"
    Inc_Relation_Types ||--o{ Statement : "作为谓词(关系)"
```

---

## 4. 主题数仓 ER 图

```mermaid
erDiagram
    %% ===== 主题数仓（分析层） =====

    Entity_Id_Mappings {
        bigint id PK "主键ID"
        string source_id FK "数据源ID"
        string source_entity_key UK "源系统主键"
        string entity_id FK "平台实体ID"
        string entity_class_id FK "实体类ID"
        float mapping_confidence "映射置信度"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    Indicator_Dictionary {
        string indicator_id PK "指标ID(MI开头)"
        string indicator_name "指标名称"
        text description "描述"
        text calc_expression "计算口径"
        string unit "计量单位"
        enum time_granularity "时间粒度"
        enum status "状态"
        int version "版本号"
        datetime created_at "创建时间"
        datetime updated_at "更新时间"
    }

    Indicator_Ontology_Mappings {
        bigint id PK "主键ID"
        string indicator_id FK "指标ID"
        string ontology_property_id FK "本体属性ID"
        text mapping_rule "映射规则"
        datetime created_at "创建时间"
    }

    Dwd_Entity_Fact {
        string entity_id FK "实体ID"
        string class_id FK "本体类ID"
        string entity_category "五维分类"
        string chain_id "产业链ID"
        string region_id "区域ID"
        string time_id "时间ID"
        string metric_id FK "指标ID"
        decimal metric_value "指标值"
        string unit "计量单位"
        string source_id FK "数据源ID"
        float quality_score "质量评分"
        date dt PK "分区日期"
    }

    %% 主题数仓关系
    Ds_Basic_Info ||--o{ Entity_Id_Mappings : "来源映射"
    Entity ||--o{ Entity_Id_Mappings : "实体映射"
    Inc_Ontology_Classes ||--o{ Entity_Id_Mappings : "类型映射"

    Indicator_Dictionary ||--o{ Indicator_Ontology_Mappings : "语义映射"
    Inc_Property_Definitions ||--o{ Indicator_Ontology_Mappings : "属性映射"

    Entity ||--o{ Dwd_Entity_Fact : "事实记录"
    Inc_Ontology_Classes ||--o{ Dwd_Entity_Fact : "分类"
    Indicator_Dictionary ||--o{ Dwd_Entity_Fact : "指标定义"
    Ds_Basic_Info ||--o{ Dwd_Entity_Fact : "数据来源"
```

---

## 5. 向量库与图谱库 ER 图

```mermaid
erDiagram
    %% ===== 向量库（Milvus） =====

    Entity_Vectors {
        string entity_id PK "实体ID"
        string entity_category "五维分类(分区键)"
        array embedding "向量(1024维)"
        string model_version "模型版本"
        bigint updated_at "更新时间戳"
    }

    Statement_Vectors {
        string statement_id PK "Statement ID"
        string statement_type "语句类型(分区键)"
        array embedding "向量(1024维)"
        string model_version "模型版本"
        bigint updated_at "更新时间戳"
    }

    Document_Vectors {
        string doc_id PK "文档ID"
        string resource_type "资源类型(分区键)"
        array embedding "向量(1024维)"
        string model_version "模型版本"
        bigint updated_at "更新时间戳"
    }

    %% ===== 图谱库（Neo4j）逻辑模型 =====

    Graph_Node {
        string entity_id PK "实体ID"
        string class_id FK "本体类ID"
        string entity_category "五维分类"
        string name "实体名称"
        json properties "属性集合"
    }

    Graph_Edge {
        string edge_id PK "边ID(ED开头)"
        string source_id FK "起点实体ID"
        string target_id FK "终点实体ID"
        string relation_type FK "关系类型ID"
        string statement_id FK "来源Statement"
        float weight "权重"
        float confidence "置信度"
        datetime begin_time "生效开始"
        datetime end_time "生效结束"
    }

    %% 向量库与源数据关系
    Entity ||--|| Entity_Vectors : "向量化"
    Statement ||--|| Statement_Vectors : "向量化"
    Standard_Document ||--|| Document_Vectors : "向量化"

    %% 图谱与知识网络关系
    Entity ||--|| Graph_Node : "映射节点"
    Statement ||--|| Graph_Edge : "派生边"
    Inc_Relation_Types ||--o{ Graph_Edge : "定义关系"
```

---

## 6. 全局表间关系总览

```mermaid
erDiagram
    %% ===== 跨层核心关系总览 =====

    %% 数据资源层
    DS_BASIC_INFO ||--o{ DS_ACCESS_TASK : "配置任务"
    DS_ACCESS_TASK ||--o{ DS_ACCESS_RECORD : "产生记录"
    DS_BASIC_INFO ||--o{ RESOURCE_DOCUMENT : "数据来源"
    RESOURCE_DOCUMENT ||--o| MINIO_FILE_INDEX : "关联文件"

    %% 资源层到知识网络
    RESOURCE_DOCUMENT ||--|| STANDARD_DOCUMENT : "标准化"
    MINIO_FILE_INDEX ||--o| STANDARD_DOCUMENT : "文件来源"
    STANDARD_DOCUMENT ||--o{ MICRO_DOCUMENT : "切分微文档"

    %% 知识网络内部
    MICRO_DOCUMENT ||--o{ CONTEXT : "证据来源"
    ENTITY ||--o{ STATEMENT : "作为主体"
    ENTITY ||--o{ STATEMENT : "作为客体"
    STATEMENT ||--|| CONTEXT : "关联上下文"

    %% 本体模型驱动
    ONTOLOGY_CLASS ||--o{ ENTITY : "实例化"
    ONTOLOGY_CLASS ||--o{ STANDARD_DOCUMENT : "分类"
    PROPERTY_DEF ||--o{ STATEMENT : "属性谓词"
    RELATION_TYPE ||--o{ STATEMENT : "关系谓词"

    %% 知识网络到派生存储
    ENTITY ||--|| ENTITY_VECTORS : "向量化"
    STATEMENT ||--|| GRAPH_EDGE : "派生图谱边"
    ENTITY ||--|| GRAPH_NODE : "派生图谱节点"

    %% 知识网络到数仓
    ENTITY ||--o{ DWD_ENTITY_FACT : "事实记录"
    ENTITY ||--o{ ENTITY_ID_MAPPINGS : "ID映射"
    INDICATOR_DICT ||--o{ DWD_ENTITY_FACT : "指标定义"
    PROPERTY_DEF ||--o{ INDICATOR_MAPPINGS : "语义映射"
```

---

## 图例说明

|      符号      |        含义        |
|--------------|------------------|
| `\|\|--\|\|` | 一对一关系            |
| `\|\|--o{`   | 一对多关系            |
| `o{--o{`     | 多对多关系            |
| `\|\|--o\|`  | 一对零或一关系          |
| `PK`         | 主键 (Primary Key) |
| `FK`         | 外键 (Foreign Key) |
| `UK`         | 唯一键 (Unique Key) |

---

## 核心数据流向

```
数据采集 → 资源层(贴源存储) → 标准化文档 → 微文档切分
                                    ↓
                          知识网络(Entity/Statement/Context)
                                    ↓
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
         图谱库(Neo4j)         向量库(Milvus)         主题数仓(Doris)
              ↓                     ↓                     ↓
              └─────────────────────┼─────────────────────┘
                                    ↓
                            数据服务层(ES/Redis/API)
```

