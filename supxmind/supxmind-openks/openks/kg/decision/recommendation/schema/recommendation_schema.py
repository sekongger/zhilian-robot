from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class RecommendationSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "Recommendation", "desc": "推荐决策"}],
            "relations": [],
            "fields": [],
        }
