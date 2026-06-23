import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

# Ensure module-level GraphitiService initialization has required env vars.
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "password123")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("OPENAI_API_BASE", "https://example.invalid/v1")
os.environ.setdefault("OPENAI_MODEL", "test-model")

from services import storyline_service as ss  # noqa: E402


def _feature(
    *,
    episode_uuid: str,
    title: str,
    content: str,
    source: str = "test_source",
    entity_ids: set[str] | None = None,
    hotness: float = 1.0,
    event_type: str = "unknown",
    embedding: list[float] | None = None,
    is_low_quality: bool = False,
) -> ss.EpisodeFeature:
    now = datetime.now(timezone.utc)
    ids = entity_ids or set()
    return ss.EpisodeFeature(
        uuid=episode_uuid,
        title=title,
        content=content,
        source=source,
        publish_at=now,
        hotness=hotness,
        entity_ids=ids,
        entity_names={entity_id: entity_id for entity_id in ids},
        entity_weights={entity_id: 1.0 for entity_id in ids},
        source_quality=1.0,
        event_type=event_type,
        semantic_embedding=embedding,
        is_low_quality=is_low_quality,
    )


class StorylineServicePureFunctionTests(unittest.TestCase):
    def test_similarity_can_be_positive_without_shared_entities(self) -> None:
        left = _feature(
            episode_uuid="ep-left",
            title="Company A 发布机器人平台",
            content="A 发布通用控制平台",
            entity_ids={"A"},
            event_type="release",
            embedding=[1.0, 0.0],
        )
        right = _feature(
            episode_uuid="ep-right",
            title="Company A 推出机器人控制底座",
            content="控制底座提升开发效率",
            entity_ids={"B"},
            event_type="release",
            embedding=[0.98, 0.02],
        )

        with patch.multiple(
            ss,
            STORYLINE_WEIGHT_ENTITY=0.45,
            STORYLINE_WEIGHT_SEMANTIC=0.30,
            STORYLINE_WEIGHT_TIME=0.15,
            STORYLINE_WEIGHT_EVENT=0.10,
            STORYLINE_MAX_DAYS=21.0,
        ):
            detail = ss._episode_similarity_details(left, right)

        self.assertEqual(int(detail["shared_entities"]), 0)
        self.assertGreater(detail["semantic_score"], 0.95)
        self.assertGreater(detail["total_score"], 0.2)

    def test_should_link_uses_stricter_threshold_for_low_quality(self) -> None:
        left = _feature(
            episode_uuid="ep-lq",
            title="快讯",
            content="短内容",
            entity_ids={"X"},
            is_low_quality=True,
        )
        right = _feature(
            episode_uuid="ep-normal",
            title="标准资讯",
            content="较完整内容",
            entity_ids={"Y"},
        )

        weak_detail = {
            "total_score": 0.50,
            "semantic_score": 0.72,
            "time_score": 0.88,
            "shared_entities": 0.0,
        }
        strong_detail = {
            "total_score": 0.70,
            "semantic_score": 0.72,
            "time_score": 0.88,
            "shared_entities": 0.0,
        }

        with patch.multiple(
            ss,
            STORYLINE_LINK_THRESHOLD=0.45,
            STORYLINE_LOW_QUALITY_LINK_THRESHOLD=0.60,
        ):
            self.assertFalse(ss._should_link(left, right, weak_detail))
            self.assertTrue(ss._should_link(left, right, strong_detail))

    def test_low_quality_and_exclusion_rules(self) -> None:
        low_quality = _feature(
            episode_uuid="ep-low",
            title="短讯",
            content="很短",
            entity_ids={"Z"},
            hotness=0.2,
        )
        excluded = _feature(
            episode_uuid="ep-excluded",
            title="",
            content="",
            entity_ids=set(),
            hotness=0.1,
        )

        with patch.multiple(
            ss,
            STORYLINE_LOW_QUALITY_MIN_CONTENT_CHARS=30,
            STORYLINE_LOW_QUALITY_MAX_ENTITY_COUNT=1,
            STORYLINE_LOW_QUALITY_MAX_HOTNESS=0.8,
            STORYLINE_EXCLUDE_MIN_CONTENT_CHARS=12,
            STORYLINE_EXCLUDE_MAX_HOTNESS=0.2,
        ):
            self.assertTrue(ss._is_low_quality_episode(low_quality))
            self.assertTrue(ss._should_exclude_episode(excluded))

    def test_joined_reason_contains_key_signals(self) -> None:
        left = _feature(
            episode_uuid="ep-a",
            title="A 融资",
            content="A 完成融资",
            entity_ids={"A"},
            event_type="financing",
        )
        right = _feature(
            episode_uuid="ep-b",
            title="A 获得追加融资",
            content="投资方追加投资",
            entity_ids={"A"},
            event_type="financing",
        )
        detail = {
            "shared_entities": 2.0,
            "semantic_score": 0.82,
            "event_type_score": 1.0,
            "time_score": 0.77,
        }
        reason = ss._build_joined_reason(left, right, detail)

        self.assertIn("shared_entities=2", reason)
        self.assertIn("semantic=", reason)
        self.assertIn("event_type=financing", reason)
        self.assertIn("time_close=", reason)

    def test_cosine_similarity_handles_invalid_inputs(self) -> None:
        self.assertEqual(ss._cosine_similarity(None, [1.0, 2.0]), 0.0)
        self.assertEqual(ss._cosine_similarity([1.0], [1.0, 2.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
