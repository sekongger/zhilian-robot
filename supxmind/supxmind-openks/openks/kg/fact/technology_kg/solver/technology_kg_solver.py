from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TechnologyKgSolver(BaseSolver):
    def solve(self, query):
        return {"query": query, "results": []}
