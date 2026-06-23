from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class CapitalChainReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
