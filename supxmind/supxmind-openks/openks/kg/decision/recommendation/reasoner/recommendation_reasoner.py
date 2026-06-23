from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class RecommendationReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
