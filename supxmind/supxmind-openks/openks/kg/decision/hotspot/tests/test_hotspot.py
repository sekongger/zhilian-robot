from openks.kg.decision.hotspot import (
    HotspotBuilder,
    HotspotReasoner,
    HotspotSchema,
    HotspotSolver,
)


def test_hotspot_scaffold_runtime_contract():
    schema = HotspotSchema()
    builder = HotspotBuilder()
    reasoner = HotspotReasoner()
    solver = HotspotSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
