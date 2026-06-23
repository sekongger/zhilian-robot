"""Resolution layer for the IncCore fusion pipeline."""

from app.incore_fusion_pipeline.resolvers.conflict_resolver import ConflictResolver
from app.incore_fusion_pipeline.resolvers.entity_resolver import EntityResolver
from app.incore_fusion_pipeline.resolvers.event_resolver import EventResolver
from app.incore_fusion_pipeline.resolvers.fusion_property_merger import FusionPropertyMerger
from app.incore_fusion_pipeline.resolvers.fusion_relation_planner import FusionRelationPlanner
from app.incore_fusion_pipeline.resolvers.wikidata_canonical_matcher import WikidataCanonicalMatcher

__all__ = [
    "ConflictResolver",
    "EntityResolver",
    "EventResolver",
    "FusionPropertyMerger",
    "FusionRelationPlanner",
    "WikidataCanonicalMatcher",
]
