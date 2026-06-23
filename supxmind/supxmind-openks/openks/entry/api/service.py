from openks.common.registry import SUPPORT_MODULES, list_kg_modules
from openks.kg.fact.news_kg import NewsKgBuilder, NewsKgSolver


def get_engine_overview():
    modules = list_kg_modules()
    return {
        "name": "supxmind-openks",
        "support_modules": SUPPORT_MODULES,
        "stages": sorted({item.stage for item in modules}),
        "module_count": len(modules),
    }


def build_news_kg(*, limit: int = 20):
    builder = NewsKgBuilder()
    return builder.build_pending(limit=limit)


def get_news_kg_status():
    builder = NewsKgBuilder()
    return builder.get_status()


def query_news_kg(query):
    solver = NewsKgSolver()
    return solver.solve(query)
