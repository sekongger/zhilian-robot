# NewsReader完整表设计⽂档（含News资源表、Mention表）

设计说明：本设计严格遵循NewsReader⽂档中KnowledgeStore数据模型规范，覆盖“News资源-提及（Mention）-实体（Entity）-陈述（Statement）-上下⽂（Context）”全链路核⼼概念。补充News资源表（承载原始新闻资源）和Mention表（衔接资源与实体/陈述），与原有三张核⼼表形成完整闭环，确保数据从原始资源导⼊到知识提取、存储、追溯的全流程完整性与语义⼀致性，适配新闻领域知识融合、语义查询、事件关联等核⼼业务场景。

# ⼀、核⼼表设计（按数据流转链路排序）

# 1. News资源表（t_news_resource）

核⼼说明：承载原始新闻资源数据，作为知识提取的数据源基础，对应NewsReader⽂档中“Resource”概念的新闻领域具体化。记录新闻的基础信息、存储信息及管理元数据，URI由系统⽣成唯⼀标识。

<table><tr><td>字段名</td><td>数据类型</td><td>是否主键</td><td>是否可为空</td><td>默认值</td><td>字段说明</td><td>文档依据</td></tr><tr><td>resource Uri</td><td>VARCHAR(255)</td><td>是</td><td>否</td><td>-</td><td>新闻资源唯一标识，由系统生成（格式示例：http://newsreader/resource/news/001）</td><td>文档2.1节：Resource的URI由系统生成，与Entity的外部分配URI区分</td></tr><tr><td>news_title</td><td>VARCHAR(200)</td><td>否</td><td>否</td><td>-</td><td>新闻标题</td><td>文档2.2节：Resource需记录资源核心描述信息，标题为新闻资源核心属性</td></tr><tr><td>news_content</td><td>LONGTEXT</td><td>否</td><td>否</td><td>-</td><td>新闻正文内容（原始文本）</td><td>文档2.1节：Resource是知识提取的原始数据载体，</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td>正文为提取核心数据源</td></tr><tr><td>publisher</td><td>VARCHAR(100)</td><td>否</td><td>否</td><td>-</td><td>新闻发布机构(如“人民日报”“新华社”)</td><td>附录C:dc:publisher属性定义,用于记录资源发布方</td></tr><tr><td>publish_time</td><td>DATETIME</td><td>否</td><td>否</td><td>-</td><td>新闻发布时间(精确到分钟)</td><td>附录C:dc:date属性定义,用于记录资源发布时间</td></tr><tr><td>news_url</td><td>VARCHAR(500)</td><td>否</td><td>是</td><td>NULL</td><td>新闻原始链接(若为网络新闻)</td><td>文档2.2节:Resource可关联原始来源链接,便于溯源</td></tr><tr><td>storage_path</td><td>VARCHAR(500)</td><td>否</td><td>否</td><td>-</td><td>新闻资源存储路径(如对象存储URL、本地文件路径)</td><td>文档4.1节:系统需记录资源存储位置,支持资源复用与管理</td></tr><tr><td>resource_status</td><td>TINYINT(1)</td><td>否</td><td>否</td><td>1</td><td>资源状态:1=有效(可用于知识提取),0=无效(废弃/错误)</td><td>文档4.2节:系统需记录数据管理状态,支持资源筛选与管理</td></tr><tr><td>create_time</td><td>DATETIME</td><td>否</td><td>否</td><td>CURRENT_TIMESTAMP</td><td>资源入库时间(系统自动记录)</td><td>文档4.2节:系统需记录数据管理相关元数据,支持入库追溯</td></tr></table>

# 2. Mention表（t_mention）

核⼼说明：作为News资源与Entity、Statement的中间衔接层，对应NewsReader⽂档中“Mention”概念。记录新闻⽂本中实体、关系的具体提及⽚段，通过URI关联资源，通过实体URI关联标准化实体，为Statement提供提取来源追溯。

<table><tr><td>字段名</td><td>数据类型</td><td>是否主键</td><td>是否可为空</td><td>默认值</td><td>字段说明</td><td>文档依据</td></tr><tr><td>mention Uri</td><td>VARCHAR(255)</td><td>是</td><td>否</td><td>-</td><td>提及唯一标识，由系统生成（格式示例：http://newsreader/mentiOn/001）</td><td>文档2.1节：Mention的URI由系统生成，与Resource、Entity URI区分</td></tr><tr><td>resource Uri</td><td>VARCHAR(255)</td><td>否</td><td>否</td><td>-</td><td>关联News资源表的resource Uri，标识提及所在的新闻资源</td><td>文档2.1节：Mention是Resource中实体/关系的具体文本片段，需关联资源</td></tr><tr><td>mention_type</td><td>VARCHAR(50)</td><td>否</td><td>否</td><td>-</td><td>提及类型：枚举值为entity_entiOn（实体提及）、relation_entiOn（关系提及）、event_entiOn（事件提及）</td><td>文档2.2节：Mention分为实体提及、关系提及等类型，对应不同知识提取目标</td></tr><tr><td>target_entit y Uri</td><td>VARCHAR(255)</td><td>否</td><td>是</td><td>NULL</td><td>关联Entity表的entity Uri，实体提及时填写；关系/事件提及时为NULL</td><td>文档2.1节：Mention映射到标准化Entity，通过实体URI关联</td></tr><tr><td>mention_text</td><td>VARCHAR(200)</td><td>否</td><td>否</td><td>-</td><td>提及的文本片段（如新闻中“习近平总书记”“北京冬奥会”）</td><td>文档2.1节：Mention是Resource中的具体文本片段，需记录原始提及内容</td></tr><tr><td>start_offset</td><td>INT</td><td>否</td><td>否</td><td>-</td><td>提及文本在新闻正文中的起</td><td>附录C:nif:beginInd</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>始偏移量（字符级）</td><td>ex属性定义，用于定位文本片段位置</td></tr><tr><td>end_offset</td><td>INT</td><td>否</td><td>否</td><td>-</td><td>提及文本在新闻正文中的结束偏移量（字符级）</td><td>附录C:nif:endIndex属性定义，用于定位文本片段位置</td></tr><tr><td>extraction_tool</td><td>VARCHAR(100)</td><td>否</td><td>否</td><td>-</td><td>提及提取工具（如“News Reader NLP Engine”“BERT实体识别模型”）</td><td>文档4.2节：系统需记录知识提取相关元数据，支持提取过程追溯</td></tr><tr><td>confidence</td><td>DECIMAL(3,2)</td><td>否</td><td>否</td><td>0.90</td><td>提及识别置信度，取值范围0.0-1.0，量化提及识别的可靠性</td><td>文档2.2节：Mention需记录置信度信息，用于评估提取质量</td></tr></table>

# 3. Entity表（t_entity）

核⼼说明：承载新闻领域可识别的标准化实体（如⼈员、组织、地点、事件等），对应NewsReader⽂档中“Entity”概念。URI由外部分配，作为实体的全局唯⼀标识，通过与Mention、Statement的关联实现实体的来源追溯与属性描述。

<table><tr><td>字段名</td><td>数据类型</td><td>是否主键</td><td>是否可为空</td><td>默认值</td><td>字段说明</td><td>文档依据</td></tr><tr><td>entity Uri</td><td>VARCHAR(255)</td><td>是</td><td>否</td><td>-</td><td>实体唯一标识，由外部分配（格式示例：http://dbpedia/resource/Beijing）</td><td>文档2.1节：Entity的URI为外部分配，与系统生成的 Resource、Mention URI区分</td></tr><tr><td>entity_type</td><td>VARCHAR(100)</td><td>否</td><td>否</td><td>-</td><td>实体类型，枚举值包括：person（人员）、location（地点）、</td><td>文档2.2节：Entity包含人员、组织、地缘政治实体、地点、事件等类型；附录</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>organization(组织)、event(事件)、financial(金融对象)等</td><td>C:EntityType枚举定义</td></tr><tr><td>entity_label</td><td>VARCHAR(100)</td><td>否</td><td>否</td><td>-</td><td>实体标签(即实体名称,如“北京”“中国共产党”)</td><td>附录C:rdfs:label属性定义,用于记录实体的标准化名称</td></tr><tr><td>description</td><td>TEXT</td><td>否</td><td>是</td><td>NULL</td><td>实体描述信息(可选,补充实体详细说明)</td><td>文档2.1节:Entity为领域内可识别的实体,可通过描述补充实体信息</td></tr><tr><td>create_time</td><td>DATETIME</td><td>否</td><td>否</td><td>CURRENT_TIMEStamp</td><td>实体入库时间(系统自动记录)</td><td>文档4.2节:系统需记录数据管理相关元数据,支持数据追溯</td></tr><tr><td>update_time</td><td>DATETIME</td><td>否</td><td>否</td><td>CURRENT_TIMEStampON UPDATECURRENT_TIMEStamp</td><td>实体最后更新时间(系统自动更新)</td><td>文档4.2节:系统需记录数据管理相关元数据,支持数据更新追溯</td></tr></table>

# 4. Context表（t_context）

核⼼说明：承载Statement⽣效的上下⽂范围（如时间、空间、视⻆等），对应NewsReader⽂档中“Context”概念。URI由系统⽣成，与Statement为⼀对⼀关联，确保每个陈述都有明确的⽣效边界，保障知识的准确性与场景适配性。

<table><tr><td>字段名</td><td>数据类型</td><td>是否主键</td><td>是否可为空</td><td>默认值</td><td>字段说明</td><td>文档依据</td></tr><tr><td>context Uri</td><td>VARCHAR(255)</td><td>是</td><td>否</td><td>-</td><td>上下文唯一标识，由系统生成（格式示例：</td><td>文档2.1节：Context由系统生成URI，通过上下文元</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>http://newsreader/extension/001)</td><td>数据和URI共同标识</td></tr><tr><td>accord ing_t o</td><td>VARCHAR(25 5)</td><td>否</td><td>否</td><td>-</td><td>视角信息,标识陈述的来源视角(如“人民日报2024年5月1日报道”),对应dc:Agent类型</td><td>文档2.2节:Context通过sem:accardi ngTo描述视角信息;附录C:sem:accardi ngTo属性定义</td></tr><tr><td>begin_time stamp</td><td>DATETIME</td><td>否</td><td>否</td><td>-</td><td>上下文生效的开始时间</td><td>文档2.2节:Context通过sem:hasBegi nTimeStamp描述时间有效性;附录C:sem:hasBegi nTimeStamp属性定义</td></tr><tr><td>end_time_st amp</td><td>DATETIME</td><td>否</td><td>否</td><td>-</td><td>上下文生效的结束时间(若为瞬时事件,开始与结束时间一致)</td><td>文档2.2节:Context通过sem:hasEnd TimeStamp描述时间有效性;附录C:sem:hasEnd TimeStamp属性定义</td></tr><tr><td>spatial_info</td><td>VARCHAR(25 5)</td><td>否</td><td>是</td><td>NULL</td><td>空间信息,标识陈述生效的空间范围(如“北京市”“长江三角洲”),对应dc:Location类型</td><td>文档2.1节:Context包含空间等上下文维度;附录C:dc:spatial属性关联空间信息</td></tr><tr><td>context_com mment</td><td>TEXT</td><td>否</td><td>是</td><td>NULL</td><td>上下文补充说明(可选,</td><td>附录C:rdfs:comme</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>如“该陈述基于新闻报道的客观描述，不包含主观评价”)</td><td>nt属性用于补充说明信息</td></tr></table>

# 5. Statement表（t_statement）

核⼼说明：承载描述实体特征的<subject, predicate, object>三元组，对应NewsReader⽂档中“Statement”概念。作为知识的核⼼承载形式，与Entity（主语/宾语）、Context（⽣效上下⽂）、Mention（提取来源）均存在关联，通过元数据记录置信度、结晶状态等信息，⽀持知识融合与推理。

<table><tr><td>字段名</td><td>数据类型</td><td>是否主键</td><td>是否可为空</td><td>默认值</td><td>字段说明</td><td>文档依据</td></tr><tr><td>statement_id</td><td>BIGINT</td><td>是</td><td>否</td><td>AUTO_INCREMENT</td><td>陈述唯一标识(系统自增,便于数据库管理与查询)</td><td>文档2.1节:Statement通过&lt;subject,predicate,object,context&gt;唯一标识,增加自增ID提升管理效率</td></tr><tr><td>subject Uri</td><td>VARCHAR(255)</td><td>否</td><td>否</td><td>-</td><td>主语URI,关联Entity表的entity Uri,标识陈述描述的核心实体</td><td>文档2.1节:Statement的subject为实体;附录B:ks:subject属性关联ks:Entity</td></tr><tr><td>predicate_Urì</td><td>VARCHAR(255)</td><td>否</td><td>否</td><td>-</td><td>谓词URI,标识主语与宾语的关系或主语的属性(格式示例:http://sema nticweb.org/property/locatedIn)</td><td>文档2.1节:Statement包含predicate属性;附录B:ks:predicate属性为pdf:Property类型</td></tr><tr><td>object_cont ent</td><td>VARCHAR(255)</td><td>否</td><td>否</td><td>-</td><td>宾语内容:若为实体则存储</td><td>文档2.1节:Statement分</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td>entity_url(关联Entity表),若为属性值则存储字 面量(如“2024-05-01”“100亿 元”),若为类型则存储类 型URI</td><td>为 TypeStatem ent (object 为类型 URI)、AttributeStat ement (object为字 面量)、RelationStat ement (object为实 体URI)</td></tr><tr><td>object_type</td><td>VARCHAR(50 )</td><td>否</td><td>否</td><td>-</td><td>宾语类型:枚举值为entity(实体)、 literal(字面量)、type(类型)</td><td>文档2.1节:Statement的 object类型随陈述类型不同而变化,分为实体、字面量、类型三类</td></tr><tr><td>context Uri</td><td>VARCHAR(25 5)</td><td>否</td><td>否</td><td>-</td><td>上下文URI, 关联Context 表的 context Uri ,标识陈述生效的上下文范围</td><td>文档2.1节:Statement包含context关联;附录B:ks:context属 性关联ks:Context</td></tr><tr><td>extracted_from</td><td>VARCHAR(25 5)</td><td>否</td><td>否</td><td>-</td><td>提取来源, 关联Mention表的 mention Uri (标识陈述从哪个提及中提取)</td><td>文档2.1节:Statement包含extractedFrom关联,关联提及;附录B:ks:extracted From 属性关联ks: Mention</td></tr><tr><td>confidence</td><td>DECIMAL(3,2 )</td><td>否</td><td>否</td><td>0.95</td><td>置信度,取值范围0.0-1.0,量化陈述的可靠性</td><td>文档2.2节:Statement包含 confidence</td></tr><tr><td></td><td></td><td></td><td></td><td></td><td></td><td>属性，用于表示提取陈述的可靠性</td></tr><tr><td>crystallized</td><td>TINYINT(1)</td><td>否</td><td>否</td><td>0</td><td>是否结晶: 1=是（属于背景知识或经多次提取同化），0=否（仅来自单条新闻提取）</td><td>文档2.2节: Statement包含crystallized标志，标识是否为结晶的背景知识</td></tr><tr><td>dc_source</td><td>VARCHAR(255)</td><td>否</td><td>是</td><td>NULL</td><td>来源信息，标识背景知识的外部导入来源（如“DBPedia”“Wiki pedia”），结晶陈述时填写</td><td>文档2.2节: Statement包含dc:source属性记录背景知识来源；附录C: dc:source属性定义</td></tr><tr><td>statement_c omment</td><td>TEXT</td><td>否</td><td>是</td><td>NULL</td><td>陈述补充说明（可选，如“该陈述描述了事件的发生地点，提取自新闻正文第3段”）</td><td>附录C: rdfs:comme nth属性用于补充说明信息</td></tr></table>

# ⼆、表间关联关系详解

各表通过URI或主键形成“News资源 Mention Entity/Statement Context”的完整数据流转与追溯链路，关联关系清晰且符合NewsReader⽂档规范，具体如下：

# 1.核⼼关联链路

• News资源表 Mention表：⼀对多关系。⼀个新闻资源（resource_uri）中可包含多个提及⽚段（如多个实体、关系提及），通过resource_uri字段关联。

• Mention表 Entity表：多对⼀关系。多个提及⽚段（如新闻中不同位置对“北京”的提及）可映射到同⼀个标准化实体（entity_uri），通过target_entity_uri字段关联（仅实体提及时有效）。

Mention表 Statement表：⼀对多关系。⼀个提及⽚段可提取⽣成多个陈述（如从“北京举办冬奥会”的提及中，可提取“北京-举办-冬奥会”“冬奥会-举办地点-北京”两个陈述），通过extracted_from字段关联mention_uri。

• Entity表 Statement表：⼀对多关系。⼀个实体可作为多个陈述的主语（如“北京”可对应“北京-位于-中国”“北京-是-⾸都”等多个陈述）或宾语（如“冬奥会-举办地点-北京”），通过subject_uri和object_content（object_type=entity时）关联entity_uri。

• Context表 Statement表：⼀对⼀关系。⼀个上下⽂仅对应⼀个陈述，确保每个陈述的⽣效范围唯⼀；⼀个陈述必须关联⼀个上下⽂，通过context_uri字段关联。

# 2.关联关系图

Code block   
1 graph TD   
3 A[t_news_resource] -- resource Uri  $\rightharpoonup$  B[tmention]   
4 B -- target_entity Uri  $\rightharpoondown$  C[t-entity]   
5 B -- mention Uri  $\rightharpoonup$  D[t_statement]   
6 C -- entity Uri  $\rightharpoonup$  D   
7 D -- context Uri  $\rightharpoonup$  E[t_context]   
8 E -- according_to  $\rightharpoonup$  A   
9

# 三、设计约束与规范

# 1.数据约束

• URI唯⼀性约束：resource_uri、mention_uri、entity_uri、context_uri均需保证全局唯⼀性，符合⽂档中“URI作为唯⼀标识”的核⼼要求。

• 关联完整性约束：Mention表的resource_uri必须存在于News资源表；Statement表的subject_uri必须存在于Entity表、context_uri必须存在于Context表、extracted_from必须存在于Mention表，确保数据链路完整。

枚举值约束：entity_type、mention_type、object_type等枚举字段严格限制取值范围，需与⽂档附录C中的枚举定义⼀致，禁⽌⾃定义枚举值。

• 置信度约束：Mention表和Statement表的confidence字段取值范围严格限制为0.0-1.0，确保量化指标的有效性。

# 2.命名规范

表名规范：采⽤“t_+核⼼概念名”的格式，全部⼩写，核⼼概念名与NewsReader⽂档中的概念名称⼀致（如t_news_resource、t_mention）。

字段名规范：采⽤“⼩写字⺟ $^ +$ 下划线”的格式，核⼼字段名尽量复⽤⽂档附录C中的属性名称（如according_to、dc_source），提升与⽂档规范的兼容性。

• URI格式规范：系统⽣成的URI（resource_uri、mention_uri、context_uri）统⼀采⽤“http://newsreader/概念类型/唯⼀标识”的格式；外部分配的entity_uri采⽤现有知识库标准格式（如DBPedia、Wikipedia的URI格式）。

# 四、适配场景与扩展说明

# 1. 核⼼适配场景

• 新闻知识提取：从News资源表的原始新闻中，通过NLP⼯具提取Mention，映射到Entity，⽣成Statement，关联Context，完成从原始数据到结构化知识的转化。

• 语义查询：基于Statement表的三元组结构，⽀持SPARQL查询（如查询“北京相关的事件”“某组织的发布的新闻”），适配新闻领域语义检索需求。

• 知识融合：通过Entity表的外部URI关联现有知识库（如DBPedia），将新闻提取的知识与背景知识融合，提升知识的完整性；通过crystallized字段区分临时知识与背景知识，⽀持知识同化。

. 追溯审计：通过“News资源 Mention Statement Context”的关联链路，可反向追溯每个陈述的原始来源，适配数据审计与可靠性验证需求。

# 2.扩展说明

字段扩展：若需适配特殊新闻类型（如财经新闻、体育新闻），可在News资源表中增加“news_category”（新闻分类）字段，在Entity表中增加对应领域的专属属性字段（如财经实体的“market_value”字段）。

• 存储扩展：若新闻资源量⼤（如千万级以上），可将News资源表的news_content字段分离存储到对象存储，表中仅保留存储路径，提升查询效率；Statement表若需⽀持⼤规模三元组查询，可同步存储到Triple Store（如Fuseki），适配SPARQL⾼效查询。

• 规则扩展：可新增“推理规则表（t_inference_rule）”，存储基于Statement的推理规则（如“若A位于B，B属于C，则A属于C”），适配知识推理场景，扩展设计可参考Statement表的关联逻辑。

（注：⽂档部分内容可能由AI⽣成）
