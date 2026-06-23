from openks.kg.fact.policy_kg import (
    PolicyKgBuilder,
    PolicyKgReasoner,
    PolicyKgSchema,
    PolicyKgSolver,
)


def test_policy_kg_scaffold_runtime_contract():
    schema = PolicyKgSchema()
    builder = PolicyKgBuilder()
    reasoner = PolicyKgReasoner()
    solver = PolicyKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
