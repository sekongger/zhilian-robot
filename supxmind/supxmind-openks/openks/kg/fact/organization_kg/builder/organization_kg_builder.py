from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class OrganizationKgBuilder(BaseBuilder):
    def build(self, records):
        return list(records)
