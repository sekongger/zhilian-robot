from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class BaseKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [
                {"name": "Document", "desc": "产业文档基类"},
                {"name": "Organization", "desc": "组织主体基类"},
                {"name": "TechnologyElement", "desc": "技术要素基类"},
                {"name": "ProductElement", "desc": "产品要素基类"},
                {"name": "IndustryEvent", "desc": "产业事件基类"},
            ],
            "relations": [
                {"name": "mentions_organization", "desc": "文档提及组织", "source": "Document", "target": "Organization"},
                {"name": "mentions_technology", "desc": "文档提及技术", "source": "Document", "target": "TechnologyElement"},
                {"name": "mentions_product", "desc": "文档提及产品", "source": "Document", "target": "ProductElement"},
                {"name": "describes_event", "desc": "文档描述事件", "source": "Document", "target": "IndustryEvent"},
            ],
            "fields": [
                {"name": "canonical_id", "type": "text", "desc": "统一 ID"},
                {"name": "name", "type": "text", "desc": "标准名称"},
                {"name": "alias", "type": "text", "desc": "别名"},
                {"name": "source", "type": "text", "desc": "来源"},
                {"name": "source_url", "type": "text", "desc": "来源链接"},
                {"name": "confidence", "type": "float", "desc": "置信度"},
            ],
        }
