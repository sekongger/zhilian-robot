"""Routing schema loader for the wiki industry-chain pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional

import yaml
from pydantic import BaseModel


class RoutingRule(BaseModel):
    route: str
    module: Optional[str] = None
    property_name: Optional[str] = None
    target_type: Optional[str] = None
    edge_type: Optional[str] = None
    direction: Literal["forward", "reverse"] = "forward"


class IndustryWikiRoutingSchema:
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.categories = payload.get("categories", {}) or {}

    @classmethod
    def load(cls, path: str | Path) -> "IndustryWikiRoutingSchema":
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        return cls(payload)

    def category_target_type(self, category: str) -> Optional[str]:
        category_payload = self.categories.get(category) or {}
        return category_payload.get("target_type")

    def route(self, category: str, property_id: str) -> RoutingRule:
        category_payload = self.categories.get(category) or {}
        modules = category_payload.get("modules", {}) or {}
        for module_name, module_payload in modules.items():
            properties = module_payload.get("properties", {}) or {}
            for property_name, configured_property_id in properties.items():
                if configured_property_id != property_id:
                    continue
                edge_type = self._edge_type(module_payload, property_name)
                return RoutingRule(
                    route=module_payload.get("route", "unclaimed"),
                    module=module_name,
                    property_name=property_name,
                    target_type=module_payload.get("target_type"),
                    edge_type=edge_type,
                    direction=module_payload.get("direction") or "forward",
                )
        return RoutingRule(route="unclaimed")

    @staticmethod
    def _edge_type(module_payload: Dict[str, Any], property_name: str) -> Optional[str]:
        edges = module_payload.get("edges")
        if isinstance(edges, dict):
            return edges.get(property_name)
        return module_payload.get("edge")
