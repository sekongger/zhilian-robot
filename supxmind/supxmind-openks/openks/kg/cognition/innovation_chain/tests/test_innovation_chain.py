from openks.kg.cognition.innovation_chain import (
    InnovationChainBuilder,
    InnovationChainReasoner,
    InnovationChainSchema,
    InnovationChainSolver,
)


def test_innovation_chain_scaffold_runtime_contract():
    schema = InnovationChainSchema()
    builder = InnovationChainBuilder()
    reasoner = InnovationChainReasoner()
    solver = InnovationChainSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
