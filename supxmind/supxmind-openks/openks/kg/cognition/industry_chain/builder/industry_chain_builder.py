from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class IndustryChainBuilder(BaseBuilder):
    def build(self, records):
        return list(records)
