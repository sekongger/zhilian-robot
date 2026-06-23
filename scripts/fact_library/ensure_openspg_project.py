from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from config_common import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_ENV_PATH,
    REPO_ROOT,
    build_config_dict,
    load_settings,
    write_config,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure OpenSPG project exists for fact library.")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to env file.")
    parser.add_argument(
        "--config-path",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to kag_config.yaml to write back.",
    )
    parser.add_argument("--project-id", default=None, help="Force specific project id.")
    parser.add_argument("--host-addr", default=None, help="Override OpenSPG host address.")
    parser.add_argument("--namespace", default=None, help="Override namespace.")
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Do not push config update when project already exists.",
    )
    args = parser.parse_args()

    overrides = {
        "FACT_LIBRARY_PROJECT_ID": args.project_id,
        "OPENSPG_HOST_ADDR": args.host_addr,
        "FACT_LIBRARY_NAMESPACE": args.namespace,
    }
    settings = load_settings(
        env_file=Path(args.env_file) if args.env_file else None,
        overrides=overrides,
    )

    sys.path.insert(0, str(REPO_ROOT / "modules" / "kag"))
    from knext.project.client import ProjectClient  # noqa: WPS433

    host_addr = settings["OPENSPG_HOST_ADDR"]
    namespace = settings["FACT_LIBRARY_NAMESPACE"]
    config = build_config_dict(settings)

    client = ProjectClient(host_addr=host_addr)
    project = None
    requested_project_id = (settings.get("FACT_LIBRARY_PROJECT_ID") or "").strip()
    if requested_project_id:
        project = client.get_by_id(requested_project_id)
    if project is None:
        project = client.get_by_namespace(namespace=namespace)

    created = False
    if project is None:
        project = client.create(
            name=namespace,
            namespace=namespace,
            config=config,
            visibility=settings["FACT_LIBRARY_PROJECT_VISIBILITY"],
            tag=settings["FACT_LIBRARY_PROJECT_TAG"],
            userNo=settings["FACT_LIBRARY_PROJECT_USER_NO"],
        )
        created = True
    elif not args.no_update:
        client.update(
            id=project.id,
            namespace=namespace,
            config=config,
            visibility=settings["FACT_LIBRARY_PROJECT_VISIBILITY"],
            tag=settings["FACT_LIBRARY_PROJECT_TAG"],
            userNo=settings["FACT_LIBRARY_PROJECT_USER_NO"],
        )

    settings["FACT_LIBRARY_PROJECT_ID"] = str(project.id)
    write_config(settings, Path(args.config_path))

    print(
        json.dumps(
            {
                "created": created,
                "project_id": project.id,
                "namespace": namespace,
                "host_addr": host_addr,
                "config_path": str(Path(args.config_path)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
