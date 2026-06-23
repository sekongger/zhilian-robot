from __future__ import annotations

import argparse
import json
from pathlib import Path

from config_common import DEFAULT_ENV_PATH, REPO_ROOT, load_settings


DEFAULT_SCHEMA_TEMPLATE_PATH = (
    REPO_ROOT / "modules" / "kag" / "kag" / "examples" / "fact_library" / "schema" / "FactLibrary.schema"
)


def render_schema(schema_template_path: Path, namespace: str) -> Path:
    lines = schema_template_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"schema file is empty: {schema_template_path}")
    lines[0] = f"namespace {namespace}"
    target_path = schema_template_path.parent / f"{namespace}.schema"
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if target_path != schema_template_path and namespace == "FactLibrary":
        schema_template_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render fact library schema namespace from env.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to env file.")
    parser.add_argument(
        "--schema-path",
        default=str(DEFAULT_SCHEMA_TEMPLATE_PATH),
        help="Path to schema template file.",
    )
    parser.add_argument("--namespace", default=None, help="Override namespace.")
    args = parser.parse_args()

    settings = load_settings(
        env_file=Path(args.env_file) if args.env_file else None,
        overrides={"FACT_LIBRARY_NAMESPACE": args.namespace},
    )
    output_path = render_schema(Path(args.schema_path), settings["FACT_LIBRARY_NAMESPACE"])
    print(
        json.dumps(
            {
                "schema_template_path": str(Path(args.schema_path)),
                "schema_path": str(output_path),
                "namespace": settings["FACT_LIBRARY_NAMESPACE"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
