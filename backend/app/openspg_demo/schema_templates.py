"""Schema 模板（机器人主链 MVP + MyNewsDemo 真实资讯模型）。"""

import textwrap
from typing import Any, Dict, List


def _type(label: str, category: str, description: str, properties: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "label": label,
        "category": category,
        "description": description,
        "properties": properties,
    }


def _prop(name: str, data_type: str, index: str = "NONE", required: bool = False) -> Dict[str, Any]:
    return {
        "name": name,
        "type": data_type,
        "index": index,
        "required": required,
    }


def get_robot_chain_mvp_schema_template() -> Dict[str, Any]:
    """返回用于演示的 OpenSPG/KAG Schema 设计模板。"""

    types = [
        _type(
            "NewsArticle",
            "DOCUMENT",
            "产业资讯文档，作为头条追溯证据源",
            [
                _prop("title", "Text", "TEXT", True),
                _prop("summary", "Text", "TEXT"),
                _prop("content", "Text", "TEXT_AND_VECTOR"),
                _prop("url", "Text", "TEXT", True),
                _prop("sourceName", "Text", "TEXT"),
                _prop("publishTime", "Date"),
                _prop("crawlTime", "Date"),
                _prop("docHash", "Text", "TEXT", True),
                _prop("sourceCredibility", "Float"),
            ],
        ),
        _type(
            "IndustryEvent",
            "EVENT",
            "机器人主链产业动态事件（合作/融资/发布/订单/扩产/政策）",
            [
                _prop("eventType", "Text", "TEXT", True),
                _prop("eventTitle", "Text", "TEXT", True),
                _prop("eventTime", "Date"),
                _prop("eventHash", "Text", "TEXT", True),
                _prop("headlineScore", "Float"),
                _prop("confidence", "Float"),
                _prop("sourceCount", "Integer"),
                _prop("status", "Text"),
            ],
        ),
        _type(
            "Company",
            "ENTITY",
            "产业链企业（整机厂/部件厂/集成商）",
            [
                _prop("canonicalName", "Text", "TEXT", True),
                _prop("aliases", "Text", "TEXT"),
                _prop("segment", "Text", "TEXT"),
                _prop("region", "Text", "TEXT"),
            ],
        ),
        _type(
            "RobotProduct",
            "ENTITY",
            "机器人整机/产品",
            [
                _prop("canonicalName", "Text", "TEXT", True),
                _prop("productClass", "Text", "TEXT"),
            ],
        ),
        _type(
            "CoreComponent",
            "ENTITY",
            "核心零部件（减速器/伺服/控制器/传感器）",
            [
                _prop("canonicalName", "Text", "TEXT", True),
                _prop("componentClass", "Text", "TEXT"),
            ],
        ),
        _type(
            "Technology",
            "ENTITY",
            "机器人相关技术（视觉/控制/具身智能等）",
            [
                _prop("canonicalName", "Text", "TEXT", True),
                _prop("techClass", "Text", "TEXT"),
            ],
        ),
        _type(
            "Organization",
            "ENTITY",
            "协会/政府/园区/高校等组织",
            [
                _prop("canonicalName", "Text", "TEXT", True),
                _prop("orgType", "Text", "TEXT"),
            ],
        ),
    ]

    relations = [
        {
            "label": "reports",
            "from": "NewsArticle",
            "to": "IndustryEvent",
            "description": "文档报道某事件",
        },
        {
            "label": "mentions",
            "from": "NewsArticle",
            "to": ["Company", "RobotProduct", "CoreComponent", "Technology", "Organization"],
            "description": "文档提及实体（便于检索与追溯）",
        },
        {
            "label": "involves",
            "from": "IndustryEvent",
            "to": ["Company", "Organization"],
            "description": "事件涉及组织/企业",
        },
        {
            "label": "targets",
            "from": "IndustryEvent",
            "to": ["RobotProduct", "CoreComponent", "Technology"],
            "description": "事件目标对象",
        },
        {
            "label": "affects",
            "from": "IndustryEvent",
            "to": ["Company", "CoreComponent", "RobotProduct"],
            "description": "事件影响对象",
        },
    ]

    return {
        "schema_name": "zhilian_robot_chain_headlines_mvp",
        "namespace": "robot_chain_demo",
        "version": "v1",
        "scope": "机器人主链MVP（整机厂+核心零部件+集成商）",
        "types": types,
        "relations": relations,
        "event_taxonomy": [
            "cooperation",
            "financing",
            "product_release",
            "order",
            "capacity_expansion",
            "policy",
        ],
        "notes": [
            "首期以事件中心建模，文档保留为证据源，便于产业头条去重与追溯。",
            "后续可扩展到人形机器人专题及事件演化推理。",
        ],
    }


def get_my_news_demo_schema_script() -> str:
    """返回用于 OpenSPG 建模的 MyNewsDemo schema DSL。"""

    return (
        textwrap.dedent(
            """
            namespace MyNewsDemo

            Outline(标题大纲): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		content(内容): Text
            			index: TextAndVector
            	relations:
            		childOf(子标题): Outline
            		sourceChunk(关联): Chunk

            AtomicQuery(原子问): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		title(标题): Text
            			index: TextAndVector
            	relations:
            		relatedTo(相关): KnowledgeUnit
            		similar(相似问题): AtomicQuery
            		sourceChunk(关联文本块): Chunk

            Institution(科研机构): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            			index: TextAndVector
            		hotScore(综合热度): Float
            		instType(机构类型): InstitutionType
            		location(区域): Location
            	relations:
            		belongTo(量知技术节点): LzTechNode
            		belongTo(量知产业链): LzIndustry
            		belongTo(量知ICD产业节点): LzICDProductNode
            		develops(研发技术): Technology
            		produces(生产产品): Product

            LzIndustry(量知产业链): ConceptType
            	hypernymPredicate: isA

            TaxOfPerson(人物分类): ConceptType
            	hypernymPredicate: isA

            KnowledgeUnit(知识点): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		content(内容): Text
            			index: TextAndVector
            		desc(描述): Text
            			index: TextAndVector
            		extendedKnowledge(关联外扩知识点): Text
            		knowledgeType(知识类型): Text
            		ontology(本体): Text
            		relatedQuery(关联问): AtomicQuery
            		structedContent(结构化文本): Text
            			index: TextAndVector

            Document(资讯文档): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		commentCount(评论量): Integer
            		crawlTime(抓取时间): Text
            		publishTime(发布时间): Text
            		sentiment(情感倾向): Text
            			constraint: Enum="正向,中立,负向"
            		shareCount(转载量): Integer
            		source(来源媒体): Text
            		title(标题): Text
            		url(链接): Text
            		viewCount(阅读量): Integer
            	relations:
            		mentionsCompany(提及公司): Company
            		mentionsPerson(提及人物): Person
            		mentionsProduct(提及产品): Product
            		mentionsTech(提及技术): Technology

            LzICDProductNode(量知ICD产业节点): ConceptType
            	hypernymPredicate: isA

            Person(人物): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		affiliationCom(所属公司): Company
            		affiliationInst(所属机构): Institution
            		hotScore(综合热度): Float
            		role(角色): TaxOfPerson

            Company(公司): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		companyType(公司类型): CompanyType
            		hotScore(综合热度): Float
            		location(区域): Location
            	relations:
            		belongTo(量知技术节点): LzTechNode
            		belongTo(量知产业链): LzIndustry
            		belongTo(量知ICD产业节点): LzICDProductNode
            		competesWith(竞争对手): Company
            		corationCom(合作伙伴): Company
            		corationInst(合作机构): Institution
            		develops(研发技术): Technology
            		investsIn(投资): Company
            		produces(生产产品): Product
            		suppliedBy(供应商): Company

            KnowledgePoint(知识点): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		confidence(置信度): Float
            		evidenceText(证据文本): Text
            		extractTime(抽取时间): Text
            		objectName(客体名): Text
            		predicateName(关系名): Text
            		subjectName(主体名): Text
            	relations:
            		fromChunk(源自文本块): Chunk
            		linkObjCompany(链接客体公司): Company
            		linkObjInst(链接客体机构): Institution
            		linkObjPerson(链接客体人物): Person
            		linkObjProduct(链接客体产品): Product
            		linkObjTech(链接客体技术): Technology
            		linkSubjCompany(链接主体公司): Company
            		linkSubjInst(链接主体机构): Institution
            		linkSubjPerson(链接主体人物): Person
            		linkSubjProduct(链接主体产品): Product
            		linkSubjTech(链接主体技术): Technology

            Summary(文本摘要): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		content(内容): Text
            			index: TextAndVector
            	relations:
            		childOf(子摘要): Summary
            		sourceChunk(关联): Chunk

            Location(区域): ConceptType
            	hypernymPredicate: locateAt

            Product(产品): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		applicationCase(使用案例): Text
            			index: TextAndVector
            		applicationScenes(应用领域): Text
            			constraint: MultiValue
            		brand(品牌): Text
            		channel(销售渠道): Product
            			constraint: MultiValue
            		equipment(生产设备): Product
            			constraint: MultiValue
            		hotScore(综合热度): Float
            		modelNumber(型号参数): Text
            		officialName(标准名): Product
            		releaseDate(发布日期): Text
            		synonyms(同义词): Product
            			constraint: MultiValue
            	relations:
            		belongTo(量知产业链): LzIndustry
            		belongTo(量知ICD产业节点): LzICDProductNode

            CompanyType(公司类型): ConceptType
            	hypernymPredicate: isA

            Table(表格): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		afterText(后缀): Text
            			index: TextAndVector
            		beforeText(前缀): Text
            			index: TextAndVector
            		content(内容): Text
            			index: TextAndVector
            	relations:
            		sourceChunk(关联): Chunk

            Chunk(文本块): IndexType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		content(内容): Text
            			index: TextAndVector

            LzTechNode(量知技术节点): ConceptType
            	hypernymPredicate: isA

            InstitutionType(机构类型): ConceptType
            	hypernymPredicate: isA

            Technology(技术): EntityType
            	properties:
            		description(描述): Text
            		name(名称): Text
            		hotScore(综合热度): Float
            		maturityLevel(成熟度): Text
            	relations:
            		belongTo(量知技术节点): LzTechNode
            		belongTo(量知产业链): LzIndustry
            		dependsOn(依赖于): Technology
            """
        ).strip()
        + "\n"
    )
