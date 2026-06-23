from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class ReportKgReasoner(BaseReasoner):
    def infer(self, facts):
        return list(facts)
