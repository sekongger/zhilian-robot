from openks.kg.fact.organization_kg import (
    OrganizationKgBuilder,
    OrganizationKgReasoner,
    OrganizationKgSchema,
    OrganizationKgSolver,
)


def test_organization_kg_scaffold_runtime_contract():
    schema = OrganizationKgSchema()
    builder = OrganizationKgBuilder()
    reasoner = OrganizationKgReasoner()
    solver = OrganizationKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
