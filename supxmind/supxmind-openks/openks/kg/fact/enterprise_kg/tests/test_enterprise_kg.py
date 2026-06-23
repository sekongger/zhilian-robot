from openks.kg.fact.enterprise_kg import (
    EnterpriseKgBuilder,
    EnterpriseKgReasoner,
    EnterpriseKgSchema,
    EnterpriseKgSolver,
)


def test_enterprise_kg_scaffold_runtime_contract():
    schema = EnterpriseKgSchema()
    builder = EnterpriseKgBuilder()
    reasoner = EnterpriseKgReasoner()
    solver = EnterpriseKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
