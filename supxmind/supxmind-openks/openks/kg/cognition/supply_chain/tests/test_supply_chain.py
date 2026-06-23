from openks.kg.cognition.supply_chain import (
    SupplyChainBuilder,
    SupplyChainReasoner,
    SupplyChainSchema,
    SupplyChainSolver,
)


def test_supply_chain_scaffold_runtime_contract():
    schema = SupplyChainSchema()
    builder = SupplyChainBuilder()
    reasoner = SupplyChainReasoner()
    solver = SupplyChainSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
