from openks.kg.fact.technology_kg import (
    TechnologyKgBuilder,
    TechnologyKgReasoner,
    TechnologyKgSchema,
    TechnologyKgSolver,
)


def test_technology_kg_scaffold_runtime_contract():
    schema = TechnologyKgSchema()
    builder = TechnologyKgBuilder()
    reasoner = TechnologyKgReasoner()
    solver = TechnologyKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
