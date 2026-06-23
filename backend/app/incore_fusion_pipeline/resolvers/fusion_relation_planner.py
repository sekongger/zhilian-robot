"""Plan how v2 relations should enter the unified graph."""

from __future__ import annotations

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import FusionRelationDecisionDTO, V2SourceEdgeDTO


class FusionRelationPlanner:
    """Classify v2 predicates into canonical, fact, or attach-only layers."""

    CANONICAL_PREDICATES = {
        "belongsToIndustry",
        "manufacturer",
        "belongsToProduct",
        "coreTechnology",
        "shareholder",
        "supplier",
        "customer",
        "invest",
        "childOrganization",
        "region",
    }
    FACT_PREDICATES = {
        "mentions",
        "anchor_entity",
        "subject",
        "object",
        "location",
        "source_document",
        "source_chunk",
    }

    def plan(
        self,
        edge: V2SourceEdgeDTO,
        *,
        resolved_subject_graph_id: str | None,
        resolved_object_graph_id: str | None,
    ) -> FusionRelationDecisionDTO:
        predicate = edge.predicate
        if predicate == "is_a":
            decision = "merge_canonical"
            target_layer = "canonical"
            predicate = "belongsToProduct"
        elif predicate in self.CANONICAL_PREDICATES:
            decision = "merge_canonical"
            target_layer = "canonical"
        elif predicate in self.FACT_PREDICATES:
            decision = "attach_fact"
            target_layer = "fact"
        else:
            decision = "attach_only"
            target_layer = "evidence"

        warnings = []
        if not resolved_subject_graph_id or not resolved_object_graph_id:
            warnings.append("missing_resolved_endpoint")

        return FusionRelationDecisionDTO(
            source_relation_type=edge.predicate,
            source_edge_uuid=edge.source_edge_uuid,
            subject_source_uuid=edge.subject_source_uuid,
            object_source_uuid=edge.object_source_uuid,
            resolved_subject_graph_id=resolved_subject_graph_id,
            resolved_object_graph_id=resolved_object_graph_id,
            decision=decision,
            target_layer=target_layer,
            predicate=predicate,
            evidence_refs=[edge.source_edge_uuid],
            warnings=warnings,
        )
