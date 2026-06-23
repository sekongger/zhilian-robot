from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TechnologyKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "TechnologyKg", "desc": "技术知识库"}],
            "relations": [],
            "fields": [],
        }
