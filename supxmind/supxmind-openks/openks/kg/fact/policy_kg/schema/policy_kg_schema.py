from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class PolicyKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "PolicyKg", "desc": "政策知识库"}],
            "relations": [],
            "fields": [],
        }
