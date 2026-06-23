from __future__ import annotations

import json
import logging
from typing import Any

import openai
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import ModelSize
from graphiti_core.llm_client.errors import RateLimitError
from graphiti_core.prompts.models import Message
from pydantic import BaseModel
from pydantic import ValidationError

from services.graphiti_attr_sanitizer import (
    SANITIZE_MODE_OFF,
    get_flatten_max_depth,
    get_sanitize_mode,
    sanitize_attributes_payload,
)

logger = logging.getLogger(__name__)


class OpenAIGenericCompatClient(OpenAIGenericClient):
    """
    Compatibility wrapper for OpenAI-compatible models with imperfect JSON-schema adherence.

    Some providers return `entities` instead of Graphiti's expected `extracted_entities`
    for entity extraction responses. This adapter normalizes the payload shape.
    """

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            try:
                return int(raw)
            except ValueError:
                return None
        return None

    @classmethod
    def _normalize_extracted_entities_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if "extracted_entities" in payload:
            return payload

        raw_entities = payload.get("entities")
        if not isinstance(raw_entities, list):
            return payload

        normalized_entities: list[dict[str, Any]] = []
        for item in raw_entities:
            if isinstance(item, str):
                name = item.strip()
                if name:
                    normalized_entities.append({"name": name, "entity_type_id": 0})
                continue

            if not isinstance(item, dict):
                continue

            name = ""
            for candidate in (
                item.get("name"),
                item.get("entity_name"),
                item.get("entity"),
                item.get("text"),
                item.get("value"),
            ):
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
                    break
            if not name:
                continue

            entity_type_id = (
                cls._coerce_int(item.get("entity_type_id"))
                or cls._coerce_int(item.get("type_id"))
                or cls._coerce_int(item.get("entity_type"))
                or 0
            )
            normalized_entities.append({"name": name, "entity_type_id": entity_type_id})

        patched = dict(payload)
        patched["extracted_entities"] = normalized_entities
        return patched

    @classmethod
    def _normalize_node_resolutions_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        raw_resolutions = payload.get("entity_resolutions")
        if not isinstance(raw_resolutions, list):
            raw_resolutions = payload.get("resolutions")
        if not isinstance(raw_resolutions, list):
            raw_resolutions = payload.get("results")
        if not isinstance(raw_resolutions, list):
            return payload

        normalized_resolutions: list[dict[str, Any]] = []
        for idx, item in enumerate(raw_resolutions):
            if not isinstance(item, dict):
                continue

            rid = cls._coerce_int(item.get("id"))
            if rid is None:
                rid = idx

            name = ""
            for candidate in (item.get("name"), item.get("entity_name"), item.get("entity")):
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
                    break

            duplicate_name = ""
            for candidate in (
                item.get("duplicate_name"),
                item.get("duplicate"),
                item.get("matched_name"),
                item.get("match_name"),
            ):
                if isinstance(candidate, str):
                    duplicate_name = candidate.strip()
                    break

            duplicate_candidate_id = (
                cls._coerce_int(item.get("duplicate_candidate_id"))
                or cls._coerce_int(item.get("duplicate_id"))
                or cls._coerce_int(item.get("candidate_id"))
                or cls._coerce_int(item.get("target_id"))
                or cls._coerce_int(item.get("resolved_id"))
            )
            if duplicate_candidate_id is None:
                duplicate_candidate_id = -1

            normalized_resolutions.append(
                {
                    "id": rid,
                    "name": name,
                    "duplicate_name": duplicate_name,
                    "duplicate_candidate_id": duplicate_candidate_id,
                }
            )

        patched = dict(payload)
        patched["entity_resolutions"] = normalized_resolutions
        return patched

    @classmethod
    def _normalize_extracted_edges_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if "edges" in payload and isinstance(payload.get("edges"), list):
            return payload

        candidates = None
        for key in ("extracted_facts", "facts", "relations"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break

        if not isinstance(candidates, list):
            return payload

        normalized_edges: list[dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            # Keep all keys and ensure required attributes map exists.
            edge = dict(item)
            if not isinstance(edge.get("attributes"), dict):
                edge["attributes"] = {}
            normalized_edges.append(edge)

        patched = dict(payload)
        patched["edges"] = normalized_edges
        return patched

    @classmethod
    def _normalize_summarized_entities_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        if "summaries" in payload and isinstance(payload.get("summaries"), list):
            return payload

        candidates = None
        for key in ("entities", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = value
                break

        if candidates is None and isinstance(payload, dict):
            # Some providers return a single object instead of {"summaries":[...]}.
            if isinstance(payload.get("name"), str) and isinstance(payload.get("summary"), str):
                candidates = [payload]

        if not isinstance(candidates, list):
            return payload

        normalized: list[dict[str, Any]] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            summary = item.get("summary")
            if isinstance(name, str) and name.strip() and isinstance(summary, str) and summary.strip():
                normalized.append({"name": name.strip(), "summary": summary.strip()})

        patched = dict(payload)
        patched["summaries"] = normalized
        return patched

    @staticmethod
    def _is_attribute_extraction_prompt(prompt_name: str | None) -> bool:
        return prompt_name in {
            "extract_nodes.extract_attributes",
            "extract_edges.extract_attributes",
        }

    @staticmethod
    def _extract_json_payload(raw: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return text

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            while lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        if text and text[0] in "{[":
            return text

        first_obj = text.find("{")
        last_obj = text.rfind("}")
        if first_obj != -1 and last_obj > first_obj:
            return text[first_obj:last_obj + 1]

        first_arr = text.find("[")
        last_arr = text.rfind("]")
        if first_arr != -1 and last_arr > first_arr:
            return text[first_arr:last_arr + 1]

        return text

    async def _generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int = 16384,
        model_size: ModelSize = ModelSize.medium,
    ) -> dict[str, Any]:
        openai_messages = []
        for message in messages:
            message.content = self._clean_input(message.content)
            if message.role == "user":
                openai_messages.append({"role": "user", "content": message.content})
            elif message.role == "system":
                openai_messages.append({"role": "system", "content": message.content})

        try:
            response_format: dict[str, Any] = {"type": "json_object"}
            if response_model is not None:
                schema_name = getattr(response_model, "__name__", "structured_response")
                json_schema = response_model.model_json_schema()
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": json_schema,
                    },
                }

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format=response_format,  # type: ignore[arg-type]
            )

            result = response.choices[0].message.content or ""
            normalized = self._extract_json_payload(result)
            try:
                return json.loads(normalized)
            except json.JSONDecodeError:
                logger.warning(
                    "LLM returned non-JSON payload for parsing. raw_preview=%s",
                    result[:240],
                )
                raise
        except openai.RateLimitError as exc:
            raise RateLimitError from exc

    @classmethod
    def _sanitize_attributes_response(
        cls,
        response: dict[str, Any],
        response_model: type[BaseModel],
        prompt_name: str | None,
    ) -> dict[str, Any]:
        if not cls._is_attribute_extraction_prompt(prompt_name):
            return response

        if not isinstance(response, dict):
            return response

        mode = get_sanitize_mode()
        if mode == SANITIZE_MODE_OFF:
            return response

        max_depth = get_flatten_max_depth()
        sanitized, stats = sanitize_attributes_payload(response, mode=mode, max_depth=max_depth)
        if not sanitized and response:
            logger.warning(
                "Attribute sanitization dropped all fields (mode=%s, depth=%s, prompt=%s).",
                mode,
                max_depth,
                prompt_name,
            )
            return response

        try:
            response_model.model_validate(sanitized)
        except ValidationError:
            # Sanitized payload may no longer match strict schema typing.
            # This is acceptable for attribute extraction because Graphiti writes it as attributes map.
            pass

        if stats.changed:
            logger.warning(
                "Sanitized attribute payload for Neo4j safety (mode=%s, depth=%s, flattened=%s, jsonified=%s, dropped=%s, prompt=%s).",
                mode,
                max_depth,
                stats.flattened_fields,
                stats.jsonified_fields,
                stats.dropped_fields,
                prompt_name,
            )

        return sanitized

    async def generate_response(
        self,
        messages: list[Message],
        response_model: type[BaseModel] | None = None,
        max_tokens: int | None = None,
        model_size: ModelSize = ModelSize.medium,
        group_id: str | None = None,
        prompt_name: str | None = None,
    ) -> dict[str, Any]:
        response = await super().generate_response(
            messages=messages,
            response_model=response_model,
            max_tokens=max_tokens,
            model_size=model_size,
            group_id=group_id,
            prompt_name=prompt_name,
        )
        if isinstance(response, dict) and response_model is not None:
            model_name = getattr(response_model, "__name__", "")
            if model_name == "ExtractedEntities":
                if "extracted_entities" not in response and "entities" in response:
                    normalized = self._normalize_extracted_entities_payload(response)
                    logger.warning(
                        "Normalized extraction response shape from `entities` to `extracted_entities`."
                    )
                    return normalized
            elif model_name == "NodeResolutions":
                normalized = self._normalize_node_resolutions_payload(response)
                if normalized is not response:
                    logger.warning(
                        "Normalized dedupe response shape to `entity_resolutions`."
                    )
                    return normalized
            elif model_name == "ExtractedEdges":
                normalized = self._normalize_extracted_edges_payload(response)
                if normalized is not response:
                    logger.warning(
                        "Normalized edge extraction response shape to `edges`."
                    )
                    return normalized
            elif model_name == "SummarizedEntities":
                if "summaries" not in response:
                    normalized = self._normalize_summarized_entities_payload(response)
                    if "summaries" in normalized:
                        logger.warning(
                            "Normalized summary response shape to `summaries` array."
                        )
                        return normalized
            if self._is_attribute_extraction_prompt(prompt_name):
                return self._sanitize_attributes_response(
                    response=response,
                    response_model=response_model,
                    prompt_name=prompt_name,
                )
        return response
