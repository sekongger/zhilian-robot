from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TrendBuilder(BaseBuilder):
    def build(self, records):
        return list(records)
