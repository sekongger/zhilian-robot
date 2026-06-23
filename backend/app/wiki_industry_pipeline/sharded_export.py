"""Sharded local export for full Wikidata industry-chain graph extraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.wiki_industry_pipeline.candidate_filter import (
    DEFAULT_TYPE_WHITELIST_PATH,
    WikiEntityCandidateFilter,
    build_entity_context,
)
from app.wiki_industry_pipeline.claim_extractor import WikiClaimExtractor
from app.wiki_industry_pipeline.claim_router import WikiClaimRouter
from app.wiki_industry_pipeline.coverage_reporter import WikiCoverageReporter
from app.wiki_industry_pipeline.dto import WikiEntityCandidateDTO, WikiGraphBuildBatchDTO
from app.wiki_industry_pipeline.graph_mapper import WikiIndustryGraphMapper
from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records


@dataclass(frozen=True)
class ShardedExportResultDTO:
    output_dir: str
    manifest_path: str
    shard_count: int
    raw_record_count: int
    total_candidate_count: int
    total_node_count: int
    total_edge_count: int


def export_wikidata_graph_shards(
    *,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    output_dir: str | Path,
    domain: str = "all_industry",
    type_whitelist_path: str | Path | None = None,
    limit: int | None = None,
    candidate_limit: int | None = None,
    shard_candidate_size: int = 5000,
    resume: bool = False,
) -> ShardedExportResultDTO:
    if shard_candidate_size <= 0:
        raise ValueError("shard_candidate_size must be positive.")

    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    schema = IndustryWikiRoutingSchema.load(routing_schema_path)
    candidate_filter = WikiEntityCandidateFilter.for_domain(
        domain,
        type_whitelist_path or DEFAULT_TYPE_WHITELIST_PATH,
    )
    claim_extractor = WikiClaimExtractor()
    claim_router = WikiClaimRouter(schema)
    graph_mapper = WikiIndustryGraphMapper()
    coverage_reporter = WikiCoverageReporter()

    raw_record_count = 0
    total_candidate_count = 0
    total_node_count = 0
    total_edge_count = 0
    shard_index = 0
    current_candidates: List[WikiEntityCandidateDTO] = []
    current_entity_contexts: dict[str, dict] = {}
    shard_records_seen = 0
    manifest_shards = []
    manifest_path = resolved_output_dir / "manifest.json"
    skip_records = 0
    resume_cursor = None
    base_raw_record_count = 0
    latest_resume_cursor = None

    if resume and manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        shard_index = int(existing_manifest.get("shard_count") or 0)
        saved_raw_record_count = int(existing_manifest.get("raw_record_count") or 0)
        total_candidate_count = int(existing_manifest.get("total_candidate_count") or 0)
        total_node_count = int(existing_manifest.get("total_node_count") or 0)
        total_edge_count = int(existing_manifest.get("total_edge_count") or 0)
        manifest_shards = list(existing_manifest.get("shards") or [])
        resume_cursor = existing_manifest.get("resume_cursor")
        latest_resume_cursor = resume_cursor
        if resume_cursor is not None:
            base_raw_record_count = saved_raw_record_count
            raw_record_count = saved_raw_record_count
            skip_records = 0
        else:
            base_raw_record_count = 0
            raw_record_count = 0
            skip_records = saved_raw_record_count

    checkpoint_interval = 50000

    def _cursor_checkpoint(stream_count: int, cursor: int) -> None:
        nonlocal latest_resume_cursor
        absolute_raw_record_count = base_raw_record_count + stream_count
        latest_resume_cursor = cursor
        if absolute_raw_record_count % checkpoint_interval != 0:
            return
        _write_manifest(
            manifest_path=manifest_path,
            domain=domain,
            dump_path=dump_path,
            routing_schema_path=routing_schema_path,
            type_whitelist_path=type_whitelist_path,
            limit=limit,
            candidate_limit=candidate_limit,
            shard_candidate_size=shard_candidate_size,
            shard_count=shard_index,
            raw_record_count=absolute_raw_record_count,
            total_candidate_count=total_candidate_count,
            total_node_count=total_node_count,
            total_edge_count=total_edge_count,
            manifest_shards=manifest_shards,
            status="running",
            resume_cursor=cursor,
        )

    try:
        stream_record_count = 0
        for record in iter_wikidata_records(
            dump_path,
            limit=limit,
            skip_records=0,
            resume_cursor=resume_cursor,
            cursor_callback=_cursor_checkpoint if str(dump_path).startswith(("http://", "https://")) else None,
            cursor_interval=checkpoint_interval,
        ):
            stream_record_count += 1
            raw_record_count = base_raw_record_count + stream_record_count
            if raw_record_count <= skip_records:
                continue
            shard_records_seen += 1
            current_entity_contexts[record.entity_id] = build_entity_context(record.raw)
            candidate = candidate_filter.filter_record(record)
            if candidate is None:
                continue
            current_candidates.append(candidate)
            total_candidate_count += 1

            if len(current_candidates) >= shard_candidate_size:
                shard_index += 1
                shard = _write_shard(
                    output_dir=resolved_output_dir,
                    shard_index=shard_index,
                    domain=domain,
                    candidates=current_candidates,
                    raw_record_count=shard_records_seen,
                    claim_extractor=claim_extractor,
                    claim_router=claim_router,
                    graph_mapper=graph_mapper,
                    coverage_reporter=coverage_reporter,
                    entity_contexts=current_entity_contexts,
                )
                manifest_shards.append(shard)
                total_node_count += shard["node_count"]
                total_edge_count += shard["edge_count"]
                _write_manifest(
                    manifest_path=manifest_path,
                    domain=domain,
                    dump_path=dump_path,
                    routing_schema_path=routing_schema_path,
                    type_whitelist_path=type_whitelist_path,
                    limit=limit,
                    candidate_limit=candidate_limit,
                    shard_candidate_size=shard_candidate_size,
                    shard_count=shard_index,
                    raw_record_count=raw_record_count,
                    total_candidate_count=total_candidate_count,
                    total_node_count=total_node_count,
                    total_edge_count=total_edge_count,
                    manifest_shards=manifest_shards,
                    status="running",
                    resume_cursor=latest_resume_cursor,
                )
                print(
                    f"[wiki-industry-export] shard={shard_index} raw={raw_record_count} "
                    f"candidates={total_candidate_count} nodes={total_node_count} edges={total_edge_count}",
                    flush=True,
                )
                current_candidates = []
                current_entity_contexts = {}
                shard_records_seen = 0

            if candidate_limit is not None and total_candidate_count >= candidate_limit:
                break
    except Exception as exc:
        _write_manifest(
            manifest_path=manifest_path,
            domain=domain,
            dump_path=dump_path,
            routing_schema_path=routing_schema_path,
            type_whitelist_path=type_whitelist_path,
            limit=limit,
            candidate_limit=candidate_limit,
            shard_candidate_size=shard_candidate_size,
            shard_count=shard_index,
            raw_record_count=raw_record_count,
            total_candidate_count=total_candidate_count,
            total_node_count=total_node_count,
            total_edge_count=total_edge_count,
            manifest_shards=manifest_shards,
            status="interrupted",
            resume_cursor=latest_resume_cursor,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        raise

    if current_candidates:
        shard_index += 1
        shard = _write_shard(
            output_dir=resolved_output_dir,
            shard_index=shard_index,
            domain=domain,
            candidates=current_candidates,
            raw_record_count=shard_records_seen,
            claim_extractor=claim_extractor,
            claim_router=claim_router,
            graph_mapper=graph_mapper,
            coverage_reporter=coverage_reporter,
            entity_contexts=current_entity_contexts,
        )
        manifest_shards.append(shard)
        total_node_count += shard["node_count"]
        total_edge_count += shard["edge_count"]
        _write_manifest(
            manifest_path=manifest_path,
            domain=domain,
            dump_path=dump_path,
            routing_schema_path=routing_schema_path,
            type_whitelist_path=type_whitelist_path,
            limit=limit,
            candidate_limit=candidate_limit,
            shard_candidate_size=shard_candidate_size,
            shard_count=shard_index,
            raw_record_count=raw_record_count,
            total_candidate_count=total_candidate_count,
            total_node_count=total_node_count,
            total_edge_count=total_edge_count,
            manifest_shards=manifest_shards,
            status="running",
            resume_cursor=latest_resume_cursor,
        )
        print(
            f"[wiki-industry-export] shard={shard_index} raw={raw_record_count} "
            f"candidates={total_candidate_count} nodes={total_node_count} edges={total_edge_count}",
            flush=True,
        )

    _write_manifest(
        manifest_path=manifest_path,
        domain=domain,
        dump_path=dump_path,
        routing_schema_path=routing_schema_path,
        type_whitelist_path=type_whitelist_path,
        limit=limit,
        candidate_limit=candidate_limit,
        shard_candidate_size=shard_candidate_size,
        shard_count=shard_index,
        raw_record_count=raw_record_count,
        total_candidate_count=total_candidate_count,
        total_node_count=total_node_count,
        total_edge_count=total_edge_count,
        manifest_shards=manifest_shards,
        status="completed",
        resume_cursor=latest_resume_cursor,
    )
    return ShardedExportResultDTO(
        output_dir=str(resolved_output_dir),
        manifest_path=str(manifest_path),
        shard_count=shard_index,
        raw_record_count=raw_record_count,
        total_candidate_count=total_candidate_count,
        total_node_count=total_node_count,
        total_edge_count=total_edge_count,
    )


def _write_shard(
    *,
    output_dir: Path,
    shard_index: int,
    domain: str,
    candidates: List[WikiEntityCandidateDTO],
    entity_contexts: dict[str, dict],
    raw_record_count: int,
    claim_extractor: WikiClaimExtractor,
    claim_router: WikiClaimRouter,
    graph_mapper: WikiIndustryGraphMapper,
    coverage_reporter: WikiCoverageReporter,
) -> dict:
    claims = []
    routed_claims = []
    unclaimed = []
    for candidate in candidates:
        candidate_claims = claim_extractor.extract(candidate)
        claims.extend(candidate_claims)
        subject_category = candidate.candidate_categories[0] if candidate.candidate_categories else "Technology"
        for claim in candidate_claims:
            routed = claim_router.route(claim, subject_category=subject_category)
            if routed.route == "unclaimed":
                unclaimed.append(claim)
            else:
                routed_claims.append(routed)

    batch = WikiGraphBuildBatchDTO(
        source_batch_id=f"wiki_industry_{domain}_shard_{shard_index:06d}",
        entities=candidates,
        claims=claims,
        routed_claims=routed_claims,
        unclaimed=unclaimed,
        entity_contexts=entity_contexts,
        metadata={"domain": domain, "shard_index": shard_index},
    )
    graph_batch = graph_mapper.map_batch(batch)
    stub_node_count = sum(
        1
        for node in [
            *graph_batch.concept_nodes,
            *graph_batch.entity_nodes,
            *graph_batch.event_nodes,
            *graph_batch.document_nodes,
            *graph_batch.chunk_nodes,
        ]
        if node.properties.get("_semanticType") == "stub"
    )
    report = coverage_reporter.report(
        batch,
        raw_record_count=raw_record_count,
        stub_node_count=stub_node_count,
    )

    graph_path = output_dir / f"graph_batch_{shard_index:06d}.json"
    report_path = output_dir / f"coverage_report_{shard_index:06d}.json"
    _write_json(graph_path, graph_batch.model_dump(mode="json"))
    _write_json(report_path, report.model_dump(mode="json"))
    return {
        "shard_index": shard_index,
        "graph_batch_path": str(graph_path),
        "coverage_report_path": str(report_path),
        "candidate_count": len(candidates),
        "node_count": graph_batch.node_count(),
        "edge_count": graph_batch.edge_count(),
        "raw_record_count": raw_record_count,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_manifest(
    *,
    manifest_path: Path,
    domain: str,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    type_whitelist_path: str | Path | None,
    limit: int | None,
    candidate_limit: int | None,
    shard_candidate_size: int,
    shard_count: int,
    raw_record_count: int,
    total_candidate_count: int,
    total_node_count: int,
    total_edge_count: int,
    manifest_shards: list[dict],
    status: str,
    resume_cursor: int | None = None,
    error: dict | None = None,
) -> None:
    payload = {
        "status": status,
        "error": error,
        "domain": domain,
        "dump_path": str(dump_path),
        "routing_schema_path": str(routing_schema_path),
        "type_whitelist_path": str(type_whitelist_path or DEFAULT_TYPE_WHITELIST_PATH),
        "limit": limit,
        "candidate_limit": candidate_limit,
        "resume_supported": True,
        "shard_candidate_size": shard_candidate_size,
        "shard_count": shard_count,
        "raw_record_count": raw_record_count,
        "total_candidate_count": total_candidate_count,
        "total_node_count": total_node_count,
        "total_edge_count": total_edge_count,
        "shards": manifest_shards,
    }
    if resume_cursor is not None:
        payload["resume_cursor"] = resume_cursor
    _write_json(manifest_path, payload)
