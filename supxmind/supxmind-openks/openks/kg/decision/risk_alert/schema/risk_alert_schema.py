from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class RiskAlertSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "RiskAlert", "desc": "风险预警"}],
            "relations": [],
            "fields": [],
        }
