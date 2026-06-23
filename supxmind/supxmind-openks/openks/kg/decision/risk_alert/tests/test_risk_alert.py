from openks.kg.decision.risk_alert import (
    RiskAlertBuilder,
    RiskAlertReasoner,
    RiskAlertSchema,
    RiskAlertSolver,
)


def test_risk_alert_scaffold_runtime_contract():
    schema = RiskAlertSchema()
    builder = RiskAlertBuilder()
    reasoner = RiskAlertReasoner()
    solver = RiskAlertSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
