#!/usr/bin/env python3
"""Expand the IncCore Wikidata type whitelist through P279 subclass links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from app.wiki_industry_pipeline.type_taxonomy_expander import expand_type_whitelist


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="expand-wikidata-type-whitelist")
    parser.add_argument(
        "--input",
        default="configs/industry_wiki/wikidata_type_whitelist.yaml",
        help="Seed whitelist YAML path.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Expanded whitelist YAML path.",
    )
    parser.add_argument("--profile", default="all_industry")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--limit-per-seed", type=int, default=200)
    args = parser.parse_args(argv)

    result = expand_type_whitelist(
        input_path=Path(args.input),
        output_path=Path(args.output),
        profile=args.profile,
        max_depth=args.max_depth,
        limit_per_seed=args.limit_per_seed,
    )
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
