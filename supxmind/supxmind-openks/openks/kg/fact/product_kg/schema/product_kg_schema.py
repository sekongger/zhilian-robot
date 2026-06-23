from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver

class ProductKgSchema(BaseSchema):
    def describe(self):
        return {
            "entities": [{"name": "ProductKg", "desc": "产品知识库"}],
            "relations": [],
            "fields": [],
        }
