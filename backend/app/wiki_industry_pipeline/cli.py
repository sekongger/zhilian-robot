"""CLI entry points for the wiki industry-chain base graph MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from app.incore_fusion_pipeline.importers.openspg_importer import OpenSPGImporter
from app.wiki_industry_pipeline.candidate_filter import (
    DEFAULT_TYPE_WHITELIST_PATH,
    WikiEntityCandidateFilter,
    build_entity_context,
)
from app.wiki_industry_pipeline.claim_extractor import WikiClaimExtractor
from app.wiki_industry_pipeline.claim_router import WikiClaimRouter
from app.wiki_industry_pipeline.coverage_reporter import WikiCoverageReporter
from app.wiki_industry_pipeline.dto import WikiGraphBuildBatchDTO
from app.wiki_industry_pipeline.graph_mapper import WikiIndustryGraphMapper
from app.wiki_industry_pipeline.kag_adapter import import_wikidata_dump_with_kag_components
from app.wiki_industry_pipeline.schema_loader import IndustryWikiRoutingSchema
from app.wiki_industry_pipeline.sharded_export import export_wikidata_graph_shards
from app.wiki_industry_pipeline.wikidata_fetcher import WikidataOnlineFetcher, write_records_jsonl
from app.wiki_industry_pipeline.wikidata_reader import iter_wikidata_records


def run_build(
    *,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    domain: str = "robotics",
    type_whitelist_path: str | Path | None = None,
    limit: Optional[int] = None,
    candidate_limit: Optional[int] = None,
    output_path: str | Path,
    report_path: str | Path,
    dry_run: bool = True,
    import_to_openspg: bool = False,
    project_id: int | None = None,
    openspg_base_url: str | None = None,
    import_result_path: str | Path | None = None,
    importer: OpenSPGImporter | None = None,
    kag_writer=None,
):
    schema = IndustryWikiRoutingSchema.load(routing_schema_path)
    candidate_filter = WikiEntityCandidateFilter.for_domain(
        domain,
        type_whitelist_path or DEFAULT_TYPE_WHITELIST_PATH,
    )
    claim_extractor = WikiClaimExtractor()
    claim_router = WikiClaimRouter(schema)

    raw_count = 0
    candidates = []
    claims = []
    routed_claims = []
    unclaimed = []
    entity_contexts = {}

    for record in iter_wikidata_records(dump_path, limit=limit):
        raw_count += 1
        entity_contexts[record.entity_id] = build_entity_context(record.raw)
        candidate = candidate_filter.filter_record(record)
        if candidate is None:
            continue
        candidates.append(candidate)
        candidate_claims = claim_extractor.extract(candidate)
        claims.extend(candidate_claims)
        subject_category = candidate.candidate_categories[0] if candidate.candidate_categories else "Technology"
        for claim in candidate_claims:
            routed = claim_router.route(claim, subject_category=subject_category)
            if routed.route == "unclaimed":
                unclaimed.append(claim)
            else:
                routed_claims.append(routed)
        if candidate_limit is not None and len(candidates) >= candidate_limit:
            break

    batch = WikiGraphBuildBatchDTO(
        source_batch_id=f"wiki_industry_{domain}",
        entities=candidates,
        claims=claims,
        routed_claims=routed_claims,
        unclaimed=unclaimed,
        entity_contexts=entity_contexts,
        metadata={"domain": domain, "dry_run": dry_run, "project_id": project_id},
    )
    graph_batch = WikiIndustryGraphMapper().map_batch(batch)
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
    report = WikiCoverageReporter().report(batch, raw_record_count=raw_count, stub_node_count=stub_node_count)

    _write_json(output_path, graph_batch.model_dump(mode="json"))
    _write_json(report_path, report.model_dump(mode="json"))
    if import_to_openspg:
        if importer is not None:
            import_result = importer.import_batch(graph_batch, dry_run=False)
        else:
            import_result = import_wikidata_dump_with_kag_components(
                dump_path=dump_path,
                routing_schema_path=routing_schema_path,
                domain=domain,
                type_whitelist_path=type_whitelist_path,
                limit=limit,
                candidate_limit=candidate_limit,
                project_id=project_id,
                host_addr=openspg_base_url,
                writer=kag_writer,
            )
        if import_result_path is not None:
            _write_json(import_result_path, import_result.model_dump(mode="json"))
    return graph_batch


def run_stream_import(
    *,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    domain: str = "all_industry",
    type_whitelist_path: str | Path | None = None,
    limit: Optional[int] = None,
    candidate_limit: Optional[int] = None,
    project_id: int | None = None,
    openspg_base_url: str | None = None,
    import_result_path: str | Path | None = None,
    kag_writer=None,
):
    import_result = import_wikidata_dump_with_kag_components(
        dump_path=dump_path,
        routing_schema_path=routing_schema_path,
        domain=domain,
        type_whitelist_path=type_whitelist_path,
        limit=limit,
        candidate_limit=candidate_limit,
        project_id=project_id,
        host_addr=openspg_base_url,
        writer=kag_writer,
    )
    if import_result_path is not None:
        _write_json(import_result_path, import_result.model_dump(mode="json"))
    return import_result


def run_export_shards(
    *,
    dump_path: str | Path,
    routing_schema_path: str | Path,
    output_dir: str | Path,
    domain: str = "all_industry",
    type_whitelist_path: str | Path | None = None,
    limit: Optional[int] = None,
    candidate_limit: Optional[int] = None,
    shard_candidate_size: int = 5000,
    resume: bool = False,
):
    return export_wikidata_graph_shards(
        dump_path=dump_path,
        routing_schema_path=routing_schema_path,
        output_dir=output_dir,
        domain=domain,
        type_whitelist_path=type_whitelist_path,
        limit=limit,
        candidate_limit=candidate_limit,
        shard_candidate_size=shard_candidate_size,
        resume=resume,
    )


def run_fetch(
    *,
    seed_terms_path: str | Path,
    output_path: str | Path,
    search_limit_per_term: int = 3,
    max_entities: int = 100,
    expand_depth: int = 1,
    sparql_limit: int = 20,
    fetcher: WikidataOnlineFetcher | None = None,
):
    active_fetcher = fetcher or WikidataOnlineFetcher()
    records = active_fetcher.fetch_records_from_seed_config(
        seed_terms_path,
        search_limit_per_term=search_limit_per_term,
        max_entities=max_entities,
        expand_depth=expand_depth,
        sparql_limit=sparql_limit,
    )
    write_records_jsonl(records, output_path)
    return records


def run_fetch_build(
    *,
    seed_terms_path: str | Path,
    routing_schema_path: str | Path,
    fetched_output_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    domain: str = "robotics",
    type_whitelist_path: str | Path | None = None,
    search_limit_per_term: int = 3,
    max_entities: int = 100,
    expand_depth: int = 1,
    sparql_limit: int = 20,
    dry_run: bool = True,
    import_to_openspg: bool = False,
    project_id: int | None = None,
    openspg_base_url: str | None = None,
    import_result_path: str | Path | None = None,
    fetcher: WikidataOnlineFetcher | None = None,
    importer: OpenSPGImporter | None = None,
    kag_writer=None,
):
    run_fetch(
        seed_terms_path=seed_terms_path,
        output_path=fetched_output_path,
        search_limit_per_term=search_limit_per_term,
        max_entities=max_entities,
        expand_depth=expand_depth,
        sparql_limit=sparql_limit,
        fetcher=fetcher,
    )
    return run_build(
        dump_path=fetched_output_path,
        routing_schema_path=routing_schema_path,
        domain=domain,
        type_whitelist_path=type_whitelist_path,
        output_path=output_path,
        report_path=report_path,
        dry_run=dry_run,
        import_to_openspg=import_to_openspg,
        project_id=project_id,
        openspg_base_url=openspg_base_url,
        import_result_path=import_result_path,
        importer=importer,
        kag_writer=kag_writer,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="wiki-industry-pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch")
    fetch.add_argument("--seed-terms", required=True)
    fetch.add_argument("--output", required=True)
    fetch.add_argument("--search-limit-per-term", type=int, default=3)
    fetch.add_argument("--max-entities", type=int, default=100)
    fetch.add_argument("--expand-depth", type=int, default=1)
    fetch.add_argument("--sparql-limit", type=int, default=20)

    build = subparsers.add_parser("build")
    build.add_argument("--dump", required=True)
    build.add_argument("--routing-schema", required=True)
    build.add_argument("--domain", default="robotics")
    build.add_argument("--type-whitelist", default=None)
    build.add_argument("--limit", type=int, default=None)
    build.add_argument("--candidate-limit", type=int, default=None)
    build.add_argument("--output", required=True)
    build.add_argument("--report", required=True)
    build.add_argument("--dry-run", action="store_true")
    build.add_argument("--live-import", action="store_true")
    build.add_argument("--project-id", type=int, default=None)
    build.add_argument("--openspg-base-url", default=None)
    build.add_argument("--import-result", default=None)

    fetch_build = subparsers.add_parser("fetch-build")
    fetch_build.add_argument("--seed-terms", required=True)
    fetch_build.add_argument("--routing-schema", required=True)
    fetch_build.add_argument("--domain", default="robotics")
    fetch_build.add_argument("--type-whitelist", default=None)
    fetch_build.add_argument("--fetched-output", required=True)
    fetch_build.add_argument("--output", required=True)
    fetch_build.add_argument("--report", required=True)
    fetch_build.add_argument("--search-limit-per-term", type=int, default=3)
    fetch_build.add_argument("--max-entities", type=int, default=100)
    fetch_build.add_argument("--expand-depth", type=int, default=1)
    fetch_build.add_argument("--sparql-limit", type=int, default=20)
    fetch_build.add_argument("--dry-run", action="store_true")
    fetch_build.add_argument("--live-import", action="store_true")
    fetch_build.add_argument("--project-id", type=int, default=None)
    fetch_build.add_argument("--openspg-base-url", default=None)
    fetch_build.add_argument("--import-result", default=None)

    stream_import = subparsers.add_parser("stream-import")
    stream_import.add_argument("--dump", required=True)
    stream_import.add_argument("--routing-schema", required=True)
    stream_import.add_argument("--domain", default="all_industry")
    stream_import.add_argument("--type-whitelist", default=None)
    stream_import.add_argument("--limit", type=int, default=None)
    stream_import.add_argument("--candidate-limit", type=int, default=None)
    stream_import.add_argument("--project-id", type=int, default=None)
    stream_import.add_argument("--openspg-base-url", default=None)
    stream_import.add_argument("--import-result", default=None)

    export_shards = subparsers.add_parser("export-shards")
    export_shards.add_argument("--dump", required=True)
    export_shards.add_argument("--routing-schema", required=True)
    export_shards.add_argument("--output-dir", required=True)
    export_shards.add_argument("--domain", default="all_industry")
    export_shards.add_argument("--type-whitelist", default=None)
    export_shards.add_argument("--limit", type=int, default=None)
    export_shards.add_argument("--candidate-limit", type=int, default=None)
    export_shards.add_argument("--shard-candidate-size", type=int, default=5000)
    export_shards.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "fetch":
        run_fetch(
            seed_terms_path=args.seed_terms,
            output_path=args.output,
            search_limit_per_term=args.search_limit_per_term,
            max_entities=args.max_entities,
            expand_depth=args.expand_depth,
            sparql_limit=args.sparql_limit,
        )
    elif args.command == "build":
        run_build(
            dump_path=args.dump,
            routing_schema_path=args.routing_schema,
            domain=args.domain,
            type_whitelist_path=args.type_whitelist,
            limit=args.limit,
            candidate_limit=args.candidate_limit,
            output_path=args.output,
            report_path=args.report,
            dry_run=args.dry_run or not args.live_import,
            import_to_openspg=args.live_import and not args.dry_run,
            project_id=args.project_id,
            openspg_base_url=args.openspg_base_url,
            import_result_path=args.import_result,
        )
    elif args.command == "fetch-build":
        run_fetch_build(
            seed_terms_path=args.seed_terms,
            routing_schema_path=args.routing_schema,
            domain=args.domain,
            type_whitelist_path=args.type_whitelist,
            fetched_output_path=args.fetched_output,
            output_path=args.output,
            report_path=args.report,
            search_limit_per_term=args.search_limit_per_term,
            max_entities=args.max_entities,
            expand_depth=args.expand_depth,
            sparql_limit=args.sparql_limit,
            dry_run=args.dry_run or not args.live_import,
            import_to_openspg=args.live_import and not args.dry_run,
            project_id=args.project_id,
            openspg_base_url=args.openspg_base_url,
            import_result_path=args.import_result,
        )
    elif args.command == "stream-import":
        run_stream_import(
            dump_path=args.dump,
            routing_schema_path=args.routing_schema,
            domain=args.domain,
            type_whitelist_path=args.type_whitelist,
            limit=args.limit,
            candidate_limit=args.candidate_limit,
            project_id=args.project_id,
            openspg_base_url=args.openspg_base_url,
            import_result_path=args.import_result,
        )
    elif args.command == "export-shards":
        run_export_shards(
            dump_path=args.dump,
            routing_schema_path=args.routing_schema,
            output_dir=args.output_dir,
            domain=args.domain,
            type_whitelist_path=args.type_whitelist,
            limit=args.limit,
            candidate_limit=args.candidate_limit,
            shard_candidate_size=args.shard_candidate_size,
            resume=args.resume,
        )
    return 0


def _write_json(path: str | Path, payload: dict) -> None:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
