from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence
import inspect
import sys

from openks.common.base import BaseSchema
from openks.common.registry import get_module_spec


TYPE_MAPPING = {
    "text": "Text",
    "str": "Text",
    "string": "Text",
    "float": "Float",
    "double": "Float",
    "int": "Integer",
    "integer": "Integer",
    "long": "Integer",
    "bool": "Boolean",
    "boolean": "Boolean",
    "datetime": "Text",
    "date": "Text",
}


def load_module_schema(module_name: str) -> BaseSchema:
    spec = get_module_spec(module_name)
    if spec is None:
        raise ValueError(f"unknown OpenKS module: {module_name}")

    package_name = spec.path.replace("/", ".")
    if not package_name.startswith("openks."):
        package_name = f"openks.{package_name}"
    module = import_module(package_name)
    for _, candidate in inspect.getmembers(module, inspect.isclass):
        if candidate is BaseSchema or not issubclass(candidate, BaseSchema):
            continue
        return candidate()
    raise ValueError(f"no BaseSchema implementation found for OpenKS module: {module_name}")


def compile_module_schema(module_name: str, *, namespace: str) -> str:
    schema = load_module_schema(module_name)
    payload = schema.describe() or {}
    return compile_openks_describe_to_kag_schema(payload, namespace=namespace)


def compile_openks_describe_to_kag_schema(payload: Dict[str, Any], *, namespace: str) -> str:
    entities = [dict(item) for item in payload.get("entities") or [] if isinstance(item, dict)]
    relations = [dict(item) for item in payload.get("relations") or [] if isinstance(item, dict)]
    fields = [dict(item) for item in payload.get("fields") or [] if isinstance(item, dict)]

    relation_map: Dict[str, List[Dict[str, Any]]] = {}
    for relation in relations:
        source = str(relation.get("source") or "").strip()
        if not source:
            continue
        relation_map.setdefault(source, []).append(relation)

    lines: List[str] = [f"namespace {namespace}", ""]
    for entity in entities:
        entity_name = str(entity.get("name") or "").strip()
        if not entity_name:
            continue
        entity_desc = str(entity.get("desc") or entity_name).strip()
        lines.append(f"{entity_name}({entity_desc}): EntityType")

        property_lines = list(_build_property_lines(fields))
        relation_lines = list(_build_relation_lines(relation_map.get(entity_name, ()), namespace=namespace))
        if property_lines:
            lines.append("\tproperties:")
            lines.extend(property_lines)
        if relation_lines:
            lines.append("\trelations:")
            lines.extend(relation_lines)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def export_module_schema_to_kag_project(
    module_name: str,
    *,
    namespace: str,
    project_dir: str | Path,
    commit: bool = False,
    host_addr: str | None = None,
    project_id: int | None = None,
) -> Dict[str, Any]:
    schema_text = compile_module_schema(module_name, namespace=namespace)
    project_root = Path(project_dir)
    schema_dir = project_root / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schema_dir / f"{namespace}.schema"
    schema_path.write_text(schema_text, encoding="utf-8")

    committed = False
    if commit:
        marklang_cls = _resolve_spg_schema_marklang()
        marklang = marklang_cls(
            str(schema_path),
            host_addr=host_addr,
            project_id=project_id,
        )
        committed = bool(marklang.sync_schema())

    return {
        "module_name": module_name,
        "namespace": namespace,
        "project_dir": project_root,
        "schema_path": schema_path,
        "committed": committed,
    }


def _build_property_lines(fields: Sequence[Dict[str, Any]]) -> Iterable[str]:
    for field in fields:
        field_name = str(field.get("name") or "").strip()
        if not field_name:
            continue
        field_desc = str(field.get("desc") or field_name).strip()
        field_type = _normalize_type(field.get("type"))
        yield f"\t\t{_normalize_identifier(field_name)}({field_desc}): {field_type}"


def _build_relation_lines(relations: Sequence[Dict[str, Any]], *, namespace: str) -> Iterable[str]:
    for relation in relations:
        rel_name = str(relation.get("name") or "").strip()
        target = str(relation.get("target") or "").strip()
        if not rel_name or not target:
            continue
        rel_desc = str(relation.get("desc") or rel_name).strip()
        yield f"\t\t{_normalize_identifier(rel_name)}({rel_desc}): {target}"


def _normalize_type(type_name: Any) -> str:
    normalized = str(type_name or "Text").strip().lower()
    return TYPE_MAPPING.get(normalized, str(type_name or "Text").strip() or "Text")


def _normalize_identifier(name: str) -> str:
    parts = [part for part in str(name or "").strip().replace("-", "_").split("_") if part]
    if not parts:
        return ""
    head, *tail = parts
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _resolve_spg_schema_marklang():
    repo_root = _find_repo_root()
    kag_root = repo_root / "modules" / "kag"
    kag_root_str = str(kag_root)
    if kag_root.exists() and kag_root_str not in sys.path:
        sys.path.append(kag_root_str)

    from knext.schema.marklang.schema_ml import SPGSchemaMarkLang

    return SPGSchemaMarkLang


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "modules" / "kag").exists():
            return parent
    raise FileNotFoundError("cannot locate repository root containing modules/kag")
