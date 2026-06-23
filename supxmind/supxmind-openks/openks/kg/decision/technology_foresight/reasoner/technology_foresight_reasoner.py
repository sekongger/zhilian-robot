from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TechnologyForesightReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
