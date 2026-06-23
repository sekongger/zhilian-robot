from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


SANITIZE_MODE_OFF = "off"
SANITIZE_MODE_JSON = "json"
SANITIZE_MODE_FLATTEN = "flatten"
SANITIZE_MODE_HYBRID = "hybrid"

_VALID_MODES = {
    SANITIZE_MODE_OFF,
    SANITIZE_MODE_JSON,
    SANITIZE_MODE_FLATTEN,
    SANITIZE_MODE_HYBRID,
}


@dataclass
class SanitizationStats:
    flattened_fields: int = 0
    jsonified_fields: int = 0
    dropped_fields: int = 0

    @property
    def changed(self) -> bool:
        return (self.flattened_fields + self.jsonified_fields + self.dropped_fields) > 0


def get_sanitize_mode() -> str:
    raw = str(os.getenv("GRAPHITI_ATTR_SANITIZE_MODE", SANITIZE_MODE_HYBRID)).strip().lower()
    if raw in _VALID_MODES:
        return raw
    return SANITIZE_MODE_HYBRID


def get_flatten_max_depth() -> int:
    raw = str(os.getenv("GRAPHITI_ATTR_FLATTEN_MAX_DEPTH", "2")).strip()
    try:
        value = int(raw)
    except ValueError:
        return 2
    return max(0, min(value, 10))


def sanitize_attributes_payload(
    payload: dict[str, Any],
    mode: str,
    max_depth: int,
) -> tuple[dict[str, Any], SanitizationStats]:
    stats = SanitizationStats()
    if mode == SANITIZE_MODE_OFF:
        return dict(payload), stats

    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_str = str(key)
        fragments, fragment_stats = _sanitize_property(key_str, value, mode=mode, max_depth=max_depth)
        stats.flattened_fields += fragment_stats.flattened_fields
        stats.jsonified_fields += fragment_stats.jsonified_fields
        stats.dropped_fields += fragment_stats.dropped_fields

        if not fragments:
            stats.dropped_fields += 1
            continue

        if any(fragment_key in sanitized for fragment_key in fragments):
            fallback_key = f"{key_str}_json"
            fallback_value = _to_json_string(_normalize_for_json(value))
            if fallback_value is None:
                stats.dropped_fields += 1
                continue
            sanitized[fallback_key] = fallback_value
            stats.jsonified_fields += 1
            continue

        sanitized.update(fragments)

    return sanitized, stats


def _sanitize_property(
    key: str,
    value: Any,
    mode: str,
    max_depth: int,
) -> tuple[dict[str, Any], SanitizationStats]:
    stats = SanitizationStats()
    normalized = _normalize_for_json(value)

    if _is_primitive(normalized):
        return {key: normalized}, stats

    if isinstance(normalized, list):
        if _is_primitive_list(normalized):
            return {key: normalized}, stats
        json_value = _to_json_string(normalized)
        if json_value is None:
            stats.dropped_fields += 1
            return {}, stats
        stats.jsonified_fields += 1
        if mode == SANITIZE_MODE_JSON:
            return {key: json_value}, stats
        return {f"{key}_json": json_value}, stats

    if isinstance(normalized, dict):
        if mode == SANITIZE_MODE_JSON:
            json_value = _to_json_string(normalized)
            if json_value is None:
                stats.dropped_fields += 1
                return {}, stats
            stats.jsonified_fields += 1
            return {key: json_value}, stats

        if mode in (SANITIZE_MODE_FLATTEN, SANITIZE_MODE_HYBRID):
            flattened: dict[str, Any] = {}
            ok = _flatten_object(
                prefix=key,
                value=normalized,
                depth=0,
                max_depth=max_depth,
                out=flattened,
            )
            if ok and flattened:
                if len(flattened) > 1 or next(iter(flattened.keys())) != key:
                    stats.flattened_fields += 1
                return flattened, stats

            json_value = _to_json_string(normalized)
            if json_value is None:
                stats.dropped_fields += 1
                return {}, stats
            stats.jsonified_fields += 1
            return {f"{key}_json": json_value}, stats

    json_value = _to_json_string(normalized)
    if json_value is None:
        stats.dropped_fields += 1
        return {}, stats
    stats.jsonified_fields += 1
    return {f"{key}_json": json_value}, stats


def _flatten_object(
    prefix: str,
    value: Any,
    depth: int,
    max_depth: int,
    out: dict[str, Any],
) -> bool:
    if _is_primitive(value):
        out[prefix] = value
        return True

    if isinstance(value, list):
        if _is_primitive_list(value):
            out[prefix] = value
            return True
        return False

    if isinstance(value, dict):
        if depth >= max_depth:
            return False
        for child_key, child_value in value.items():
            child_key_str = str(child_key)
            if not child_key_str:
                child_key_str = "empty"
            merged_key = f"{prefix}__{child_key_str}" if prefix else child_key_str
            if not _flatten_object(
                prefix=merged_key,
                value=child_value,
                depth=depth + 1,
                max_depth=max_depth,
                out=out,
            ):
                return False
        return True

    return False


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return _normalize_for_json(value.value)
    if isinstance(value, dict):
        return {str(k): _normalize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, set):
        return [_normalize_for_json(item) for item in value]
    if _is_primitive(value):
        return value
    return str(value)


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _is_primitive_list(value: list[Any]) -> bool:
    return all(_is_primitive(item) for item in value)


def _to_json_string(value: Any) -> str | None:
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return None

