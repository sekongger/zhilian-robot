from openks.kg.cognition.capital_chain import (
    CapitalChainBuilder,
    CapitalChainReasoner,
    CapitalChainSchema,
    CapitalChainSolver,
)


def test_capital_chain_scaffold_runtime_contract():
    schema = CapitalChainSchema()
    builder = CapitalChainBuilder()
    reasoner = CapitalChainReasoner()
    solver = CapitalChainSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
