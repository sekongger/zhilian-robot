from openks.kg.decision.recommendation import (
    RecommendationBuilder,
    RecommendationReasoner,
    RecommendationSchema,
    RecommendationSolver,
)


def test_recommendation_scaffold_runtime_contract():
    schema = RecommendationSchema()
    builder = RecommendationBuilder()
    reasoner = RecommendationReasoner()
    solver = RecommendationSolver()

    assert schema.describe()["entities"]
    assert builder.build([{"id": 1}]) == [{"id": 1}]
    assert reasoner.infer([{"id": 1}]) == [{"id": 1}]
    assert solver.solve({"keyword": "demo"})["query"] == {"keyword": "demo"}
