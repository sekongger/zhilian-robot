from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class CapitalChainSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "CapitalChain", "desc": "资金链图谱库"}],
            "relations": [],
            "fields": [],
        }
