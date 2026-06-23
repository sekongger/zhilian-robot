"""Import Wikidata-derived IncCore graph batch rows into MySQL tables."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import pymysql


ENTERPRISE_RELATION_COLUMNS = {
    "belongsToIndustry",
    "shareholder",
    "invest",
    "childOrganization",
    "supplier",
    "customer",
    "coreTechnology",
}

PRODUCT_MODEL_RELATION_COLUMNS = {
    "belongsToProduct",
    "manufacturer",
    "coreTechnology",
}

DATE_COLUMNS = {"inception", "publishDate"}
VARCHAR_RE = re.compile(r"^varchar\((\d+)\)$", re.IGNORECASE)
ENUM_RE = re.compile(r"^enum\((.+)\)$", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Enterprise/ProductModel nodes from an IncCore graph batch into MySQL."
    )
    parser.add_argument("--graph-batch", required=True)
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT") or "3306"))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE"))
    parser.add_argument("--enterprise-table", default="wiki_enterprise_cxd")
    parser.add_argument("--product-model-table", default="wiki_product_model_cxd")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for key in ["host", "user", "password", "database"]:
        if not getattr(args, key):
            raise SystemExit(f"Missing required MySQL parameter: --{key.replace('_', '-')}")

    batch = json.loads(Path(args.graph_batch).read_text(encoding="utf-8"))
    rows = build_rows(batch)

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            enterprise_columns = fetch_table_specs(cur, args.enterprise_table)
            product_model_columns = fetch_table_specs(cur, args.product_model_table)

            enterprise_rows = filter_columns(rows["Enterprise"], enterprise_columns)
            product_model_rows = filter_columns(rows["ProductModel"], product_model_columns)

            print(f"enterprise_rows={len(enterprise_rows)} table={args.enterprise_table}")
            print(f"product_model_rows={len(product_model_rows)} table={args.product_model_table}")

            if args.dry_run:
                print_sample("enterprise_sample", enterprise_rows)
                print_sample("product_model_sample", product_model_rows)
                return 0

            enterprise_affected = upsert_rows(cur, args.enterprise_table, enterprise_rows)
            product_model_affected = upsert_rows(cur, args.product_model_table, product_model_rows)
        conn.commit()
        print(f"enterprise_upsert_affected={enterprise_affected}")
        print(f"product_model_upsert_affected={product_model_affected}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


def build_rows(batch: Mapping[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    nodes = [
        *batch.get("concept_nodes", []),
        *batch.get("entity_nodes", []),
        *batch.get("event_nodes", []),
        *batch.get("document_nodes", []),
        *batch.get("chunk_nodes", []),
    ]
    node_by_id = {node["graph_id"]: node for node in nodes}
    relations = collect_relations(batch.get("edges", []), node_by_id)

    result = {"Enterprise": [], "ProductModel": []}
    for node in nodes:
        node_type = node.get("type_name")
        if node_type == "Enterprise":
            result["Enterprise"].append(build_enterprise_row(node, relations))
        elif node_type == "ProductModel":
            result["ProductModel"].append(build_product_model_row(node, relations))
    return result


def collect_relations(
    edges: Iterable[Mapping[str, Any]], node_by_id: Mapping[str, Mapping[str, Any]]
) -> Dict[tuple[str, str], List[str]]:
    relation_values: dict[tuple[str, str], list[str]] = defaultdict(list)
    for edge in edges:
        subject_id = str(edge.get("subject_graph_id") or "")
        object_id = str(edge.get("object_graph_id") or "")
        predicate = str(edge.get("predicate") or "")
        object_name = node_name(node_by_id.get(object_id), fallback=object_id)
        key = (subject_id, predicate)
        if object_name and object_name not in relation_values[key]:
            relation_values[key].append(object_name)
    return relation_values


def build_enterprise_row(
    node: Mapping[str, Any], relations: Mapping[tuple[str, str], List[str]]
) -> Dict[str, Any]:
    props = dict(node.get("properties") or {})
    graph_id = str(node.get("graph_id") or "")
    row = {
        "id": graph_id,
        "name": node_name(node, fallback=graph_id),
        "officialName": to_text(props.get("officialName")),
        "shortName": to_text(props.get("shortName")),
        "alias": to_text(props.get("alias")),
        "description": to_text(props.get("description")),
        "unifiedSocialCreditCode": to_text(props.get("unifiedSocialCreditCode")),
        "nameEn": to_text(props.get("nameEn")),
        "officialWebsite": to_text(props.get("officialWebsite")),
        "status": to_text(props.get("status")),
        "inception": to_date(props.get("inception")),
        "companyScale": to_text(props.get("companyScale")),
        "mainBusiness": to_text(props.get("mainBusiness")),
        "businessScope": to_text(props.get("businessScope")),
        "is_valid": 1,
    }
    add_relation_columns(row, graph_id, relations, ENTERPRISE_RELATION_COLUMNS)
    return remove_empty_values(row, keep={"id", "name", "is_valid"})


def build_product_model_row(
    node: Mapping[str, Any], relations: Mapping[tuple[str, str], List[str]]
) -> Dict[str, Any]:
    props = dict(node.get("properties") or {})
    graph_id = str(node.get("graph_id") or "")
    row = {
        "id": graph_id,
        "name": node_name(node, fallback=graph_id),
        "officialName": to_text(props.get("officialName")),
        "shortName": to_text(props.get("shortName")),
        "alias": to_text(props.get("alias")),
        "description": to_text(props.get("description")),
        "brand": to_text(props.get("brand")),
        "series": to_text(props.get("series")),
        "model": to_text(props.get("model")),
        "specification": to_text(props.get("specification")),
        "publishDate": to_date(props.get("publishDate")),
        "productLifecycleStatus": to_text(props.get("productLifecycleStatus")),
        "is_valid": 1,
    }
    add_relation_columns(row, graph_id, relations, PRODUCT_MODEL_RELATION_COLUMNS)
    return remove_empty_values(row, keep={"id", "name", "is_valid"})


def add_relation_columns(
    row: Dict[str, Any],
    graph_id: str,
    relations: Mapping[tuple[str, str], List[str]],
    relation_columns: Iterable[str],
) -> None:
    for relation_name in relation_columns:
        values = relations.get((graph_id, relation_name), [])
        if values:
            row[relation_name] = ",".join(values)


def fetch_table_specs(cur, table_name: str) -> dict[str, dict[str, Any]]:
    cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
    specs: dict[str, dict[str, Any]] = {}
    for row in cur.fetchall():
        field = str(row["Field"])
        column_type = str(row["Type"] or "")
        specs[field] = {
            "type": column_type,
            "max_length": parse_varchar_length(column_type),
            "enum_values": parse_enum_values(column_type),
        }
    return specs


def filter_columns(rows: Iterable[Dict[str, Any]], table_columns: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    skipped = {"create_time", "update_time"}
    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        normalized: Dict[str, Any] = {}
        for key, value in row.items():
            if key not in table_columns or key in skipped:
                continue
            normalized[key] = normalize_value_for_column(value, table_columns[key])
        normalized_rows.append(normalized)
    return normalized_rows


def upsert_rows(cur, table_name: str, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    affected = 0
    for row in rows:
        columns = list(row.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        column_sql = ", ".join(f"`{column}`" for column in columns)
        update_columns = [column for column in columns if column != "id"]
        update_sql = ", ".join(f"`{column}`=VALUES(`{column}`)" for column in update_columns)
        if "update_time" not in columns:
            update_sql = f"{update_sql}, `update_time`=CURRENT_TIMESTAMP" if update_sql else "`update_time`=CURRENT_TIMESTAMP"
        sql = (
            f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {update_sql}"
        )
        affected += cur.execute(sql, [row[column] for column in columns])
    return affected


def node_name(node: Mapping[str, Any] | None, *, fallback: str) -> str:
    if not node:
        return fallback
    value = node.get("name") or (node.get("properties") or {}).get("name") or fallback
    return to_text(value) or fallback


def to_text(value: Any) -> str | None:
    if value in (None, "", []):
        return None
    if isinstance(value, list):
        parts = [to_text(item) for item in value]
        return ",".join(part for part in parts if part)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip() or None


def to_date(value: Any) -> str | None:
    text = to_text(value)
    if not text:
        return None
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not match:
        return None
    year, month, day = match.groups()
    if month == "00" or day == "00":
        return None
    return f"{year}-{month}-{day}"


def remove_empty_values(row: Dict[str, Any], *, keep: set[str]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key in keep or value not in (None, "", [])
    }


def parse_varchar_length(column_type: str) -> int | None:
    match = VARCHAR_RE.match(column_type.strip())
    if not match:
        return None
    return int(match.group(1))


def parse_enum_values(column_type: str) -> set[str] | None:
    match = ENUM_RE.match(column_type.strip())
    if not match:
        return None
    values = set()
    for item in match.group(1).split(","):
        value = item.strip().strip("'").strip('"')
        if value:
            values.add(value)
    return values


def normalize_value_for_column(value: Any, column_spec: Mapping[str, Any]) -> Any:
    if value in (None, "", []):
        return value
    text = str(value)
    enum_values = column_spec.get("enum_values")
    if enum_values and text not in enum_values:
        return None
    max_length = column_spec.get("max_length")
    if max_length and len(text) > int(max_length):
        return text[: int(max_length)]
    return value


def print_sample(title: str, rows: List[Dict[str, Any]]) -> None:
    print(f"{title}=")
    print(json.dumps(rows[:2], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
