from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class EnterpriseKgReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
