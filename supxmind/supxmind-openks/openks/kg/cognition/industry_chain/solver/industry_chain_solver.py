from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class IndustryChainSolver(BaseSolver):
    def solve(self, query):
        return {"query": query, "results": []}
