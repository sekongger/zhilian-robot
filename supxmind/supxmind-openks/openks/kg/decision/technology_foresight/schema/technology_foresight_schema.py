from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class TechnologyForesightSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "TechnologyForesight", "desc": "技术前瞻"}],
            "relations": [],
            "fields": [],
        }
