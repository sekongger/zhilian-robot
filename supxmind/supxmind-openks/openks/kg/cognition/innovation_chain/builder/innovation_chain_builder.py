from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class InnovationChainBuilder(BaseBuilder):
    def build(self, records):
        return list(records)
