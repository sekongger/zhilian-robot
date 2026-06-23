"""Conflict resolution utilities."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import ConflictRecordDTO, ConflictSourceDetailDTO


class ConflictResolver:
    """Resolve conflicting values and keep audit trails."""

    def resolve_field_conflict(
        self,
        *,
        graph_id: str,
        field: str,
        candidates: Iterable[Tuple[Any, float, str]],
        resolution_rule: str = "authority_priority",
    ) -> Tuple[Any, ConflictRecordDTO | None]:
        ordered = sorted(candidates, key=lambda item: item[1], reverse=True)
        if not ordered:
            return None, None

        winner_value, winner_weight, winner_source = ordered[0]
        losing_values = [value for value, _, _ in ordered[1:] if value != winner_value]
        if not losing_values:
            return winner_value, None

        record = ConflictRecordDTO(
            graph_id=graph_id,
            field=field,
            winning_value=winner_value,
            losing_values=losing_values,
            resolution_rule=resolution_rule,
            source_details=[
                ConflictSourceDetailDTO(
                    source_system=source_name,
                    value=value,
                    authority_level=weight,
                )
                for value, weight, source_name in ordered
            ],
        )
        return winner_value, record

    def resolve_property_map(
        self,
        graph_id: str,
        property_candidates: Dict[str, List[Tuple[Any, float, str]]],
    ) -> Tuple[Dict[str, Any], List[ConflictRecordDTO]]:
        resolved: Dict[str, Any] = {}
        conflicts: List[ConflictRecordDTO] = []
        for field, candidates in property_candidates.items():
            value, conflict = self.resolve_field_conflict(
                graph_id=graph_id,
                field=field,
                candidates=candidates,
            )
            if value is not None:
                resolved[field] = value
            if conflict is not None:
                conflicts.append(conflict)
        return resolved, conflicts
