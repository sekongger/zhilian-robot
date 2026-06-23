from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class RiskAlertSolver(BaseSolver):
    def solve(self, query):
        return {"query": query, "results": []}
