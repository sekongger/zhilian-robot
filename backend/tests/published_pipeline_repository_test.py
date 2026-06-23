from app.knowledge_extraction_operators.catalog_specs import PIPELINE_TEMPLATES
from app.knowledge_extraction_operators.published_pipeline_repository import PublishedPipelineRepository


class _FakeCollection:
    def __init__(self):
        self.calls = []

    def update_one(self, query, update, upsert=False):
        self.calls.append(
            {
                "query": query,
                "update": update,
                "upsert": upsert,
            }
        )


class _FakeMongo:
    def __init__(self):
        self.collection = _FakeCollection()

    def get_collection(self, _name):
        return self.collection


def test_ensure_builtin_pipelines_does_not_overlap_set_and_set_on_insert_keys():
    mongodb = _FakeMongo()
    repository = PublishedPipelineRepository(mongodb=mongodb)

    repository.ensure_builtin_pipelines(PIPELINE_TEMPLATES[:1])

    assert mongodb.collection.calls
    update = mongodb.collection.calls[0]["update"]
    set_on_insert_keys = set(update["$setOnInsert"].keys())
    set_keys = set(update["$set"].keys())
    assert not (set_on_insert_keys & set_keys)
