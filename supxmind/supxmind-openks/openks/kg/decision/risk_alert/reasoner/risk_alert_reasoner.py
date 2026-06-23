from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class RiskAlertReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
