from openks.kg.fact.report_kg import (
    ReportKgBuilder,
    ReportKgReasoner,
    ReportKgSchema,
    ReportKgSolver,
)


def test_report_kg_scaffold_runtime_contract():
    schema = ReportKgSchema()
    builder = ReportKgBuilder()
    reasoner = ReportKgReasoner()
    solver = ReportKgSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
