import unittest
from unittest.mock import patch

from services.llm_compat import OpenAIGenericCompatClient


class _AttrModel:
    @staticmethod
    def model_validate(data):
        return data


class LLMCompatTests(unittest.TestCase):
    def test_normalize_entities_key_to_extracted_entities(self) -> None:
        payload = {
            "entities": [
                {"entity_name": "Tesla", "entity_type_id": 3},
                {"name": "Humanoid Robot", "entity_type": "0"},
                "Beijing",
            ]
        }

        normalized = OpenAIGenericCompatClient._normalize_extracted_entities_payload(payload)

        self.assertIn("extracted_entities", normalized)
        extracted = normalized["extracted_entities"]
        self.assertEqual(len(extracted), 3)
        self.assertEqual(extracted[0]["name"], "Tesla")
        self.assertEqual(extracted[0]["entity_type_id"], 3)
        self.assertEqual(extracted[1]["name"], "Humanoid Robot")
        self.assertEqual(extracted[1]["entity_type_id"], 0)
        self.assertEqual(extracted[2]["name"], "Beijing")
        self.assertEqual(extracted[2]["entity_type_id"], 0)

    def test_normalize_resolutions_key_to_entity_resolutions(self) -> None:
        payload = {
            "resolutions": [
                {"id": 0, "name": "Tesla", "duplicate_name": "Tesla Inc."},
                {"name": "Beijing", "matched_name": ""},
            ]
        }

        normalized = OpenAIGenericCompatClient._normalize_node_resolutions_payload(payload)

        self.assertIn("entity_resolutions", normalized)
        resolutions = normalized["entity_resolutions"]
        self.assertEqual(len(resolutions), 2)
        self.assertEqual(resolutions[0]["id"], 0)
        self.assertEqual(resolutions[0]["name"], "Tesla")
        self.assertEqual(resolutions[0]["duplicate_name"], "Tesla Inc.")
        self.assertEqual(resolutions[0]["duplicate_candidate_id"], -1)
        self.assertEqual(resolutions[1]["id"], 1)
        self.assertEqual(resolutions[1]["name"], "Beijing")
        self.assertEqual(resolutions[1]["duplicate_name"], "")
        self.assertEqual(resolutions[1]["duplicate_candidate_id"], -1)

    def test_normalize_results_key_to_entity_resolutions(self) -> None:
        payload = {
            "results": [
                {"id": 0, "name": "Tesla", "duplicate_candidate_id": 12},
                {"id": 1, "name": "Beijing"},
            ]
        }

        normalized = OpenAIGenericCompatClient._normalize_node_resolutions_payload(payload)
        resolutions = normalized["entity_resolutions"]
        self.assertEqual(len(resolutions), 2)
        self.assertEqual(resolutions[0]["duplicate_candidate_id"], 12)
        self.assertEqual(resolutions[1]["duplicate_candidate_id"], -1)

    def test_normalize_extracted_facts_to_edges(self) -> None:
        payload = {
            "extracted_facts": [
                {"source": "A", "target": "B", "relation_type": "rel"},
                {"source": "C", "target": "D", "relation_type": "rel", "attributes": {"k": "v"}},
            ],
            "episode_indices": [],
        }
        normalized = OpenAIGenericCompatClient._normalize_extracted_edges_payload(payload)
        self.assertIn("edges", normalized)
        self.assertEqual(len(normalized["edges"]), 2)
        self.assertEqual(normalized["edges"][0]["attributes"], {})
        self.assertEqual(normalized["edges"][1]["attributes"], {"k": "v"})

    def test_normalize_single_summary_object_to_summaries(self) -> None:
        payload = {
            "name": "Mongolian",
            "summary": "A language family used in cross-border communication scenarios.",
            "labels": ["Entity"],
        }
        normalized = OpenAIGenericCompatClient._normalize_summarized_entities_payload(payload)
        self.assertIn("summaries", normalized)
        self.assertEqual(len(normalized["summaries"]), 1)
        self.assertEqual(normalized["summaries"][0]["name"], "Mongolian")

    def test_normalize_entities_list_to_summaries(self) -> None:
        payload = {
            "entities": [
                {"name": "Arabic", "summary": "Supports Arabic voice adaptation."},
                {"name": "Invalid only name"},
            ]
        }
        normalized = OpenAIGenericCompatClient._normalize_summarized_entities_payload(payload)
        self.assertIn("summaries", normalized)
        self.assertEqual(len(normalized["summaries"]), 1)
        self.assertEqual(normalized["summaries"][0]["name"], "Arabic")

    def test_sanitize_attribute_payload_hybrid(self) -> None:
        payload = {
            "country": "CN",
            "finance": {"round": "A", "meta": {"stage": "growth"}},
            "tags": ["ai", "agent"],
            "rich_list": [{"k": "v"}],
        }
        with patch("services.llm_compat.get_sanitize_mode", return_value="hybrid"), patch(
            "services.llm_compat.get_flatten_max_depth", return_value=2
        ):
            sanitized = OpenAIGenericCompatClient._sanitize_attributes_response(
                response=payload,
                response_model=_AttrModel,
                prompt_name="extract_nodes.extract_attributes",
            )

        self.assertEqual(sanitized["country"], "CN")
        self.assertEqual(sanitized["finance__round"], "A")
        self.assertEqual(sanitized["finance__meta__stage"], "growth")
        self.assertEqual(sanitized["tags"], ["ai", "agent"])
        self.assertIn("rich_list_json", sanitized)
        self.assertIsInstance(sanitized["rich_list_json"], str)

    def test_sanitize_attribute_payload_json_mode(self) -> None:
        payload = {"finance": {"round": "A", "meta": {"stage": "growth"}}}
        with patch("services.llm_compat.get_sanitize_mode", return_value="json"), patch(
            "services.llm_compat.get_flatten_max_depth", return_value=2
        ):
            sanitized = OpenAIGenericCompatClient._sanitize_attributes_response(
                response=payload,
                response_model=_AttrModel,
                prompt_name="extract_edges.extract_attributes",
            )
        self.assertIn("finance", sanitized)
        self.assertIsInstance(sanitized["finance"], str)

    def test_sanitize_attribute_payload_conflict_fallback(self) -> None:
        payload = {
            "a": {"b": 1},
            "a__b": 2,
        }
        with patch("services.llm_compat.get_sanitize_mode", return_value="hybrid"), patch(
            "services.llm_compat.get_flatten_max_depth", return_value=2
        ):
            sanitized = OpenAIGenericCompatClient._sanitize_attributes_response(
                response=payload,
                response_model=_AttrModel,
                prompt_name="extract_nodes.extract_attributes",
            )
        self.assertIn("a__b", sanitized)
        self.assertIn("a__b_json", sanitized)
        self.assertIsInstance(sanitized["a__b_json"], str)

    def test_sanitize_attribute_payload_off_mode(self) -> None:
        payload = {"finance": {"round": "A"}}
        with patch("services.llm_compat.get_sanitize_mode", return_value="off"), patch(
            "services.llm_compat.get_flatten_max_depth", return_value=2
        ):
            sanitized = OpenAIGenericCompatClient._sanitize_attributes_response(
                response=payload,
                response_model=_AttrModel,
                prompt_name="extract_nodes.extract_attributes",
            )
        self.assertEqual(sanitized, payload)

    def test_sanitize_attribute_payload_non_target_prompt(self) -> None:
        payload = {"finance": {"round": "A"}}
        with patch("services.llm_compat.get_sanitize_mode", return_value="hybrid"), patch(
            "services.llm_compat.get_flatten_max_depth", return_value=2
        ):
            sanitized = OpenAIGenericCompatClient._sanitize_attributes_response(
                response=payload,
                response_model=_AttrModel,
                prompt_name="extract_nodes.extract_text",
            )
        self.assertEqual(sanitized, payload)


if __name__ == "__main__":
    unittest.main()
