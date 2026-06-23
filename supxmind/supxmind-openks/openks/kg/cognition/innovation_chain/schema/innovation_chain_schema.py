from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class InnovationChainSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "InnovationChain", "desc": "创新链图谱库"}],
            "relations": [],
            "fields": [],
        }
