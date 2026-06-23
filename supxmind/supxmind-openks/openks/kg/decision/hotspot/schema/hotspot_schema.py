from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class HotspotSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "Hotspot", "desc": "热点分析"}],
            "relations": [],
            "fields": [],
        }
