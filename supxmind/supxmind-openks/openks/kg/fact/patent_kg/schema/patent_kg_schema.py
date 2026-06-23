from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class PatentKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "PatentKg", "desc": "专利知识库"}],
            "relations": [],
            "fields": [],
        }
