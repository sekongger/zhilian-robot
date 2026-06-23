from openks.kg.fact.encyclopedia_kg import (
    EncyclopediaKgBuilder,
    EncyclopediaKgReasoner,
    EncyclopediaKgSchema,
    EncyclopediaKgSolver,
)


def test_encyclopedia_kg_scaffold_runtime_contract():
    schema = EncyclopediaKgSchema()
    builder = EncyclopediaKgBuilder()
    reasoner = EncyclopediaKgReasoner()
    solver = EncyclopediaKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
