from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
PROJECT_ROOT = CURRENT_FILE.parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.fact_library_pipeline import FactLibraryPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fact library pipeline.")
    parser.add_argument(
        "--dataset",
        default="20260313_183538",
        help="Dataset directory name under backend/data/fact_library/raw",
    )
    parser.add_argument(
        "--raw-root",
        default=str(PROJECT_ROOT / "backend" / "data" / "fact_library" / "raw"),
        help="Root directory for raw datasets",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "backend" / "data" / "fact_library" / "processed"),
        help="Root directory for processed outputs",
    )
    parser.add_argument(
        "--output-dataset",
        default="",
        help="Optional output dataset directory name under processed root",
    )
    parser.add_argument(
        "--profile",
        default="full",
        choices=("full", "quick"),
        help="Processing profile. quick keeps only a small connected subgraph for fast end-to-end runs.",
    )
    args = parser.parse_args()

    pipeline = FactLibraryPipeline(
        raw_root=Path(args.raw_root),
        output_root=Path(args.output_root),
        profile=args.profile,
    )
    result = pipeline.run(
        dataset_name=args.dataset,
        output_dataset_name=args.output_dataset or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
