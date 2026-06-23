from openks.kg.fact.base_kg import (
    BaseKgBuilder,
    BaseKgReasoner,
    BaseKgSchema,
    BaseKgSolver,
)


def test_base_kg_scaffold_runtime_contract():
    schema = BaseKgSchema()
    builder = BaseKgBuilder()
    reasoner = BaseKgReasoner()
    solver = BaseKgSolver()

    preview = schema.describe()
    assert len(preview["entities"]) >= 4
    assert preview["relations"]
    assert preview["fields"]
    assert any(item["name"] == "Document" for item in preview["entities"])
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
