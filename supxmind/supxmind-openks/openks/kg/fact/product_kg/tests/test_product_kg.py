from openks.kg.fact.product_kg import (
    ProductKgBuilder,
    ProductKgReasoner,
    ProductKgSchema,
    ProductKgSolver,
)


def test_product_kg_scaffold_runtime_contract():
    schema = ProductKgSchema()
    builder = ProductKgBuilder()
    reasoner = ProductKgReasoner()
    solver = ProductKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
