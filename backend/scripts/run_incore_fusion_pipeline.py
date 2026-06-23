from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from app.incore_fusion_pipeline.dto.source_dto import SourceRecordDTO
from app.incore_fusion_pipeline.runners.fusion_pipeline_runner import FusionPipelineRunner


def _load_records(input_path: Path) -> List[SourceRecordDTO]:
    text = input_path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("JSON array input must contain a list of source records.")
        return [SourceRecordDTO(**item) for item in payload]

    records: List[SourceRecordDTO] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
        records.append(SourceRecordDTO(**payload))
    return records


def _write_result(result: dict, output_path: Path | None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the IncCore fusion pipeline on SourceRecordDTO JSON input.")
    parser.add_argument("--input", required=True, help="Path to JSONL or JSON array input file.")
    parser.add_argument("--project", default="IncCore", help="OpenSPG project name.")
    parser.add_argument("--namespace", default="IncCore", help="OpenSPG namespace.")
    parser.add_argument("--project-id", type=int, default=None, help="OpenSPG project id.")
    parser.add_argument("--batch-id", default="incore_fusion_cli_batch", help="Batch id for this run.")
    parser.add_argument("--output", default=None, help="Optional path to write result JSON.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Write to OpenSPG using upsertVertex/upsertEdge. Default is dry-run.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        parser.error(f"input file not found: {input_path}")

    records = _load_records(input_path)
    runner = FusionPipelineRunner()
    result = runner.run(
        records=records,
        project=args.project,
        namespace=args.namespace,
        project_id=args.project_id,
        batch_id=args.batch_id,
        dry_run=not args.live,
    )
    result_payload = result.model_dump() if hasattr(result, "model_dump") else result.dict()
    _write_result(result_payload, Path(args.output).expanduser().resolve() if args.output else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
