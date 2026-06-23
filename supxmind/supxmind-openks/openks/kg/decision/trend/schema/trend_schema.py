from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TrendSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "Trend", "desc": "趋势分析"}],
            "relations": [],
            "fields": [],
        }
