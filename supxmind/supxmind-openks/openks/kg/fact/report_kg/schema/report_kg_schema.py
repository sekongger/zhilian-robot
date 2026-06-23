from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class ReportKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "ReportKg", "desc": "研报知识库"}],
            "relations": [],
            "fields": [],
        }
