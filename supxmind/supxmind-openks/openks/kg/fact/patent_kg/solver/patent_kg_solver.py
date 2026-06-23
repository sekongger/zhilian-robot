from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class PatentKgSolver(BaseSolver):
    def solve(self, query):
        return {"query": query, "results": []}
