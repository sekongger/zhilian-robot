from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class ReportKgSolver(BaseSolver):
    def solve(self, query):
        return {"query": query, "results": []}
