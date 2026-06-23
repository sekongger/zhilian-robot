"""KAG builder adapters for the Wikidata industry-chain graph pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.incore_fusion_pipeline.dto.graph_import_dto import (
    GraphImportBatchDTO,
    GraphImportResultDTO,
)
from app.knowledge_extraction_operators.kag_bridge import (
    ensure_kag_import_path,
    ensure_kag_task_config,
    graph_batch_to_kag_subgraph,
    unwrap_kag_outputs,
)
from app.wiki_industry_pipeline.candidate_filter import (
    DEFAULT_TYPE_WHITELIST_PATH,
    WikiEntityCandidateFilter,
)
from app.wiki_industry_pipeline.claim_extractor import WikiClaimExtractor
from app.wiki_industry_pipeline.claim_router import WikiClaimRouter
from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO, WikiGraphBuildBatchDTO
from app.wiki_industry_pipeline.graph_mapper import WikiIndustryGraphMapper
from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records

ensure_kag_import_path()

from kag.builder.component.writer.kg_writer import KGWriter  # noqa: E402
from kag.builder.model.sub_graph import SubGraph  # noqa: E402
from kag.common.conf import KAGConstants  # noqa: E402
from kag.interface import MappingABC, ScannerABC  # noqa: E402
from knext.common.base.runnable import Input, Output  # noqa: E402


@ScannerABC.register("wikidata_jsonl")
@ScannerABC.register("wikidata_jsonl_scanner")
class WikidataJSONLScanner(ScannerABC):
    """Read Wikidata dump/API JSONL records into KAG structured records."""

    def __init__(self, source: str = "wikidata", limit: int | None = None, **kwargs):
        _ensure_task_config(kwargs)
        super().__init__(**kwargs)
        self.source = source
        self.limit = limit

    @property
    def input_types(self) -> Input:
        return str

    @property
    def output_types(self) -> Output:
        return Dict[str, Any]

    def load_data(self, input: Input, **kwargs) -> List[Output]:
        return [
            record.model_dump(mode="json")
            for record in iter_wikidata_records(
                input, source=self.source, limit=self.limit
            )
        ]


@MappingABC.register("incore_wikidata_claim_mapping")
@MappingABC.register("wikidata_claim_mapping")
class IncCoreWikidataClaimMapping(MappingABC):
    """Parse Wikidata claims, route them to IncCore schema, and emit a KAG SubGraph."""

    def __init__(
        self,
        routing_schema_path: str | Path,
        domain: str = "wiki_industry",
        type_whitelist_path: str | Path | None = None,
        source_batch_prefix: str = "wiki_industry",
        **kwargs,
    ):
        _ensure_task_config(kwargs)
        super().__init__(**kwargs)
        self.routing_schema_path = str(routing_schema_path)
        self.domain = domain
        self.type_whitelist_path = str(type_whitelist_path) if type_whitelist_path else None
        self.source_batch_prefix = source_batch_prefix
        self.schema = IndustryWikiRoutingSchema.load(self.routing_schema_path)
        self.candidate_filter = WikiEntityCandidateFilter.for_domain(
            domain,
            self.type_whitelist_path or DEFAULT_TYPE_WHITELIST_PATH,
        )
        self.claim_extractor = WikiClaimExtractor()
        self.claim_router = WikiClaimRouter(self.schema)
        self.graph_mapper = WikiIndustryGraphMapper()

    @property
    def input_types(self) -> Input:
        return Dict[str, Any]

    @property
    def output_types(self) -> Output:
        return SubGraph

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        graph_batch = self.map_record_to_graph_batch(input)
        if graph_batch is None:
            return []
        return [
            graph_batch_to_kag_subgraph(
                graph_batch, include_internal_properties=False
            )
        ]

    def map_record_to_graph_batch(
        self, input: Dict[str, Any] | WikiDumpRecordDTO
    ) -> GraphImportBatchDTO | None:
        record = _coerce_wikidata_record(input)
        candidate = self.candidate_filter.filter_record(record)
        if candidate is None:
            return None

        claims = self.claim_extractor.extract(candidate)
        subject_category = (
            candidate.candidate_categories[0]
            if candidate.candidate_categories
            else "Technology"
        )
        routed_claims = []
        unclaimed = []
        for claim in claims:
            routed = self.claim_router.route(claim, subject_category=subject_category)
            if routed.route == "unclaimed":
                unclaimed.append(claim)
            else:
                routed_claims.append(routed)

        batch = WikiGraphBuildBatchDTO(
            source_batch_id=f"{self.source_batch_prefix}_{self.domain}_{record.entity_id}",
            entities=[candidate],
            claims=claims,
            routed_claims=routed_claims,
            unclaimed=unclaimed,
            metadata={
                "domain": self.domain,
                "source": record.source,
                "kag_mapping": "incore_wikidata_claim_mapping",
            },
        )
        return self.graph_mapper.map_batch(batch)


def import_graph_batch_with_kag_writer(
    batch: GraphImportBatchDTO,
    *,
    project_id: int | None = None,
    host_addr: str | None = None,
    writer=None,
) -> GraphImportResultDTO:
    """Import an IncCore graph batch through KAG KGWriter."""

    resolved_project_id = project_id or batch.metadata.get("project_id")
    if writer is None:
        task_id = ensure_kag_task_config(
            host_addr=host_addr,
            project_id=int(resolved_project_id) if resolved_project_id is not None else None,
            namespace=batch.namespace,
        )
        writer = KGWriter(
            project_id=int(resolved_project_id) if resolved_project_id is not None else None,
            kag_qa_task_config_key=task_id,
        )

    sub_graph = graph_batch_to_kag_subgraph(batch, include_internal_properties=False)
    writer.invoke(sub_graph, write_ckpt=False)
    return GraphImportResultDTO(
        batch_id=batch.batch_id,
        status="live",
        dry_run=False,
        node_count=batch.node_count(),
        edge_count=batch.edge_count(),
        details={
            "project": batch.project,
            "project_id": resolved_project_id,
            "namespace": batch.namespace,
            "writer": "kag.builder.component.writer.kg_writer.KGWriter",
        },
    )


def import_wikidata_dump_with_kag_components(
    *,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    domain: str = "wiki_industry",
    type_whitelist_path: str | Path | None = None,
    limit: int | None = None,
    candidate_limit: int | None = None,
    project_id: int | None = None,
    host_addr: str | None = None,
    writer=None,
) -> GraphImportResultDTO:
    """Run Wikidata JSONL -> KAG Mapping -> KAG Writer directly from raw records."""

    task_id = ensure_kag_task_config(
        host_addr=host_addr,
        project_id=project_id,
        namespace="IncCore",
    )
    scanner = WikidataJSONLScanner(limit=limit, kag_qa_task_config_key=task_id)
    mapping = IncCoreWikidataClaimMapping(
        routing_schema_path=routing_schema_path,
        domain=domain,
        type_whitelist_path=type_whitelist_path,
        kag_qa_task_config_key=task_id,
    )
    if writer is None:
        writer = KGWriter(project_id=project_id, kag_qa_task_config_key=task_id)

    node_count = 0
    edge_count = 0
    graph_count = 0
    stopped_by = None
    for record in scanner.invoke(str(dump_path)):
        graphs = unwrap_kag_outputs(mapping.invoke(record, write_ckpt=False))
        for graph in graphs:
            node_count += len(graph.nodes)
            edge_count += len(graph.edges)
            graph_count += 1
            writer.invoke(graph, write_ckpt=False)
            if candidate_limit is not None and graph_count >= candidate_limit:
                stopped_by = "candidate_limit"
                break
        if stopped_by is not None:
            break

    return GraphImportResultDTO(
        batch_id=f"wiki_industry_{domain}",
        status="live",
        dry_run=False,
        node_count=node_count,
        edge_count=edge_count,
        details={
            "project": "IncCore",
            "project_id": project_id,
            "namespace": "IncCore",
            "writer": "kag.builder.component.writer.kg_writer.KGWriter",
            "scanner": "app.wiki_industry_pipeline.kag_adapter.WikidataJSONLScanner",
            "mapping": "app.wiki_industry_pipeline.kag_adapter.IncCoreWikidataClaimMapping",
            "graph_count": graph_count,
            "candidate_limit": candidate_limit,
            "stopped_by": stopped_by,
        },
    )


def _coerce_wikidata_record(
    input: Dict[str, Any] | WikiDumpRecordDTO
) -> WikiDumpRecordDTO:
    if isinstance(input, WikiDumpRecordDTO):
        return input
    if not isinstance(input, dict):
        raise TypeError(
            f"Wikidata KAG mapping expects a dict record, got {type(input)!r}."
        )

    if isinstance(input.get("raw"), dict):
        raw = input["raw"]
        entity_id = str(input.get("entity_id") or raw.get("id") or "").strip()
        source = str(input.get("source") or "wikidata")
    else:
        raw = input
        entity_id = str(input.get("entity_id") or input.get("id") or "").strip()
        source = str(input.get("source") or "wikidata")

    if not entity_id:
        raise ValueError("Wikidata record does not contain entity_id/id.")
    return WikiDumpRecordDTO(source=source, entity_id=entity_id, raw=raw)


def _ensure_task_config(kwargs: Dict[str, Any]) -> None:
    if kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY):
        return
    kwargs[KAGConstants.KAG_QA_TASK_CONFIG_KEY] = ensure_kag_task_config()
