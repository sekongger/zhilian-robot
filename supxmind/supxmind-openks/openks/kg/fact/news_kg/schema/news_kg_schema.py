from openks.common.base.core import BaseSchema

class NewsKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [
                {"name": "NewsDocument", "desc": "资讯文档"},
                {"name": "Enterprise", "desc": "企业主体"},
                {"name": "Technology", "desc": "技术要素"},
                {"name": "Product", "desc": "产品要素"},
                {"name": "Industry", "desc": "产业概念"},
                {"name": "Event", "desc": "资讯事件"},
            ],
            "relations": [
                {"name": "involves", "desc": "资讯涉及企业主体", "source": "NewsDocument", "target": "Enterprise"},
                {"name": "mentions_technology", "desc": "资讯提及技术要素", "source": "NewsDocument", "target": "Technology"},
                {"name": "mentions_product", "desc": "资讯提及产品要素", "source": "NewsDocument", "target": "Product"},
                {"name": "belongs_to_chain", "desc": "企业属于产业链", "source": "Enterprise", "target": "Industry"},
                {"name": "collaborates_with", "desc": "企业之间合作", "source": "Enterprise", "target": "Enterprise"},
                {"name": "develops", "desc": "企业研发技术", "source": "Enterprise", "target": "Technology"},
                {"name": "supplies_to", "desc": "企业供应产品", "source": "Enterprise", "target": "Product"},
                {"name": "co_occurs_with", "desc": "实体同文共现", "source": "Enterprise", "target": "Technology"},
                {"name": "competes_with", "desc": "企业竞争关系", "source": "Enterprise", "target": "Enterprise"},
            ],
            "fields": [
                {"name": "publish_time", "type": "datetime", "desc": "资讯发布时间"},
                {"name": "sentiment", "type": "float", "desc": "情感倾向得分"},
                {"name": "confidence", "type": "float", "desc": "抽取或推理置信度"},
            ],
        }
