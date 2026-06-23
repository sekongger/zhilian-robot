from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class CapitalChainBuilder(BaseBuilder):
    def build(self, records):
        return list(records)
