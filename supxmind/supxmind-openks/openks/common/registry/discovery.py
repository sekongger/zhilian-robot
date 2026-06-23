from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence
import tomllib


STAGE_ORDER = {"fact": 0, "cognition": 1, "decision": 2}


@dataclass(frozen=True)
class KgModuleSpec:
    name: str
    title: str
    stage: str
    owner: str
    path: str
    summary: str
    status: str = "planned"
    dependencies: Sequence[str] = ()


SUPPORT_MODULES = [
    {
        "name": "common",
        "owner": "平台共建",
        "path": "openks/common",
        "summary": "统一 schema、基类、注册表、工具与适配器。",
    },
    {
        "name": "cross",
        "owner": "云飞",
        "path": "openks/cross",
        "summary": "跨 KG 映射、调度、同步与实体对齐。",
    },
    {
        "name": "entry",
        "owner": "旭科",
        "path": "openks/entry",
        "summary": "启动装配、CLI、API 与 Agent 调用入口。",
    },
]


def _registry_root() -> Path:
    return Path(__file__).resolve().parents[2] / "kg"


def _build_spec(module_toml: Path) -> KgModuleSpec:
    payload = tomllib.loads(module_toml.read_text(encoding="utf-8"))
    stage = str(payload["stage"])
    module_root = module_toml.parent
    relative_path = module_root.relative_to(module_toml.parents[3]).as_posix()

    return KgModuleSpec(
        name=str(payload["name"]),
        title=str(payload["title"]),
        stage=stage,
        owner=str(payload["owner"]),
        path=relative_path,
        summary=str(payload["summary"]),
        status=str(payload.get("status") or "planned"),
        dependencies=tuple(payload.get("dependencies") or ()),
    )


def discover_kg_modules() -> List[KgModuleSpec]:
    modules: List[KgModuleSpec] = []
    for module_toml in _registry_root().glob("*/*/module.toml"):
        modules.append(_build_spec(module_toml))
    modules.sort(key=lambda item: (STAGE_ORDER.get(item.stage, 99), item.name))
    return modules


@lru_cache(maxsize=1)
def _cached_modules() -> tuple[KgModuleSpec, ...]:
    return tuple(discover_kg_modules())


def list_kg_modules(stage: Optional[str] = None) -> List[KgModuleSpec]:
    modules = list(_cached_modules())
    if stage is None:
        return modules
    return [item for item in modules if item.stage == stage]


def get_module_spec(name: str) -> Optional[KgModuleSpec]:
    for item in _cached_modules():
        if item.name == name:
            return item
    return None


KG_MODULES = list_kg_modules()
