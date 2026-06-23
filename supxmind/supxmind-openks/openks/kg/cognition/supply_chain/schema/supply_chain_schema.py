from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class SupplyChainSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "SupplyChain", "desc": "供应链图谱库"}],
            "relations": [],
            "fields": [],
        }
