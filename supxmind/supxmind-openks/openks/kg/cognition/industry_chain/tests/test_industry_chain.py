from openks.kg.cognition.industry_chain import (
    IndustryChainBuilder,
    IndustryChainReasoner,
    IndustryChainSchema,
    IndustryChainSolver,
)


def test_industry_chain_scaffold_runtime_contract():
    schema = IndustryChainSchema()
    builder = IndustryChainBuilder()
    reasoner = IndustryChainReasoner()
    solver = IndustryChainSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
