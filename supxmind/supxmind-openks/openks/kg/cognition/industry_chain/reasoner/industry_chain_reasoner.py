from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class IndustryChainReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
