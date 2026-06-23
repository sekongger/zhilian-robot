from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class EncyclopediaKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "EncyclopediaKg", "desc": "百科知识库"}],
            "relations": [],
            "fields": [],
        }
