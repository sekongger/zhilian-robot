from openks.kg.fact.patent_kg import (
    PatentKgBuilder,
    PatentKgReasoner,
    PatentKgSchema,
    PatentKgSolver,
)


def test_patent_kg_scaffold_runtime_contract():
    schema = PatentKgSchema()
    builder = PatentKgBuilder()
    reasoner = PatentKgReasoner()
    solver = PatentKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
