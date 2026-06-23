from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class IndustryChainSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "IndustryChain", "desc": "产业链图谱库"}],
            "relations": [],
            "fields": [],
        }
