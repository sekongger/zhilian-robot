from openks.kg.decision.trend import (
    TrendBuilder,
    TrendReasoner,
    TrendSchema,
    TrendSolver,
)


def test_trend_scaffold_runtime_contract():
    schema = TrendSchema()
    builder = TrendBuilder()
    reasoner = TrendReasoner()
    solver = TrendSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
