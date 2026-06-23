from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class OrganizationKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "OrganizationKg", "desc": "机构知识库"}],
            "relations": [],
            "fields": [],
        }
