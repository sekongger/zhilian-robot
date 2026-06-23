from __future__ import annotations

import argparse
import json
from pathlib import Path

from config_common import DEFAULT_CONFIG_PATH, DEFAULT_ENV_PATH, load_settings, write_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Render fact library kag_config.yaml from env.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to env file.")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_CONFIG_PATH),
        help="Output path of kag_config.yaml.",
    )
    parser.add_argument("--project-id", default=None, help="Override project id.")
    parser.add_argument("--host-addr", default=None, help="Override OpenSPG host addr.")
    parser.add_argument("--namespace", default=None, help="Override namespace.")
    args = parser.parse_args()

    overrides = {
        "FACT_LIBRARY_PROJECT_ID": args.project_id,
        "OPENSPG_HOST_ADDR": args.host_addr,
        "FACT_LIBRARY_NAMESPACE": args.namespace,
    }
    env_file = Path(args.env_file) if args.env_file else None
    settings = load_settings(env_file=env_file, overrides=overrides)
    output_path = write_config(settings, Path(args.output))
    print(
        json.dumps(
            {
                "config_path": str(output_path),
                "namespace": settings["FACT_LIBRARY_NAMESPACE"],
                "project_id": settings["FACT_LIBRARY_PROJECT_ID"] or None,
                "host_addr": settings["OPENSPG_HOST_ADDR"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
