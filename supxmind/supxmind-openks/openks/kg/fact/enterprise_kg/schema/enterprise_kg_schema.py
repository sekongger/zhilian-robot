from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class EnterpriseKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "EnterpriseKg", "desc": "企业知识库"}],
            "relations": [],
            "fields": [],
        }
