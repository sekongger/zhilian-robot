from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
import hashlib
import re
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .specs import ENTITY_SPECS, QUICK_ENTITY_LIMITS, SUPPORT_SPECS, TableSpec, iter_specs


class FactLibraryPipeline:
    RELATION_OUTPUT_GROUPS = {
        "institution_supported_by_company": ("institution_supported_by_company",),
        "ranking_list_includes_company": ("ranking_list_includes_company",),
        "company_has_main_product": ("company_has_main_product",),
        "patent_applicants": ("patent_applied_by_company", "patent_applied_by_institution"),
        "patent_owners": ("patent_owned_by_company", "patent_owned_by_institution"),
        "patent_inventors": ("patent_invented_by_person",),
        "project_leader": ("project_led_by_person",),
        "project_org": ("project_undertaken_by_company", "project_undertaken_by_institution"),
        "achievement_unit": (
            "achievement_completed_by_company",
            "achievement_completed_by_institution",
        ),
        "achievement_person": ("achievement_completed_by_person",),
        "article_authors": ("article_authored_by_person",),
        "article_applicants": (
            "article_published_by_company",
            "article_published_by_institution",
        ),
    }

    def __init__(self, raw_root: Path, output_root: Path, profile: str = "full"):
        self.raw_root = Path(raw_root)
        self.output_root = Path(output_root)
        self._specs = tuple(iter_specs())
        self.profile = profile
        if self.profile not in {"full", "quick"}:
            raise ValueError(f"unsupported profile: {self.profile}")

    def run(self, dataset_name: str, output_dataset_name: Optional[str] = None) -> Dict[str, object]:
        source_dir = self.raw_root / dataset_name
        if not source_dir.exists():
            raise FileNotFoundError(f"raw dataset not found: {source_dir}")

        output_name = output_dataset_name or dataset_name
        dataset_output = self.output_root / output_name
        if dataset_output.exists():
            shutil.rmtree(dataset_output)
        self._ensure_output_dirs(dataset_output)

        tables_summary: List[Dict[str, object]] = []
        filtered_rows_by_source: Dict[str, List[Dict[str, str]]] = {}

        for spec in self._specs:
            source_file = self._find_source_file(source_dir, spec.source_key)
            if source_file is None:
                tables_summary.append(
                    {
                        "source_key": spec.source_key,
                        "status": "missing",
                        "filter_rule": spec.filter_description,
                    }
                )
                continue

            source_rows = self._read_source(source_file)
            total_rows = len(source_rows)
            filtered_source_rows = self._apply_filter(source_rows, spec)
            filtered_source_rows = self._drop_duplicates(filtered_source_rows, spec.id_field)
            working_rows = self._select_columns(filtered_source_rows, spec.keep_columns)
            export_columns = spec.export_columns or spec.keep_columns
            export_rows = self._select_columns(filtered_source_rows, export_columns)
            kept_rows = len(working_rows)
            filtered_rows_by_source[spec.source_key] = working_rows

            output_path = dataset_output / spec.output_group / f"{spec.output_name}.csv"
            self._write_rows(output_path, export_columns, export_rows)

            text_rows = self._build_text_rows(working_rows, spec)
            text_path = None
            if text_rows:
                text_path = dataset_output / "texts" / f"{spec.output_name}.csv"
                self._write_rows(
                    text_path,
                    ("id", "name", "entity_type", "text", "source_table", "update_time"),
                    text_rows,
                )

            tables_summary.append(
                {
                    "source_key": spec.source_key,
                    "source_file": source_file.name,
                    "output_group": spec.output_group,
                    "output_name": spec.output_name,
                    "entity_type": spec.entity_type,
                    "filter_rule": spec.filter_description,
                    "total_rows": total_rows,
                    "kept_rows": kept_rows,
                    "dropped_rows": total_rows - kept_rows,
                    "output_path": str(output_path),
                    "text_path": str(text_path) if text_path else "",
                    "status": "ok",
                }
            )

        derived_summaries = self._export_derived_entities(dataset_output, filtered_rows_by_source)
        tables_summary.extend(derived_summaries)
        relation_summary = self._export_relations(dataset_output, filtered_rows_by_source)
        if self.profile == "quick":
            relation_summary = self._compact_quick_dataset(dataset_output, tables_summary, relation_summary)
            self._refresh_relation_summary_output_rows(dataset_output, relation_summary)
        summary_path = dataset_output / "stats" / "summary.csv"
        self._write_summary(summary_path, tables_summary)

        manifest = {
            "dataset_name": dataset_name,
            "output_dataset_name": output_name,
            "profile": self.profile,
            "raw_dir": str(source_dir),
            "output_dir": str(dataset_output),
            "generated_at": datetime.utcnow().isoformat(),
            "entity_specs": [asdict(spec) for spec in ENTITY_SPECS],
            "support_specs": [asdict(spec) for spec in SUPPORT_SPECS],
            "tables": tables_summary,
            "relations": relation_summary,
        }
        manifest_path = dataset_output / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "dataset_name": dataset_name,
            "output_dataset_name": output_name,
            "profile": self.profile,
            "output_dir": str(dataset_output),
            "summary_path": str(summary_path),
            "manifest_path": str(manifest_path),
            "tables_processed": len([item for item in tables_summary if item["status"] == "ok"]),
            "relations_generated": len(relation_summary),
        }

    def _ensure_output_dirs(self, dataset_output: Path) -> None:
        for dirname in ("entities", "support", "texts", "relations", "stats"):
            (dataset_output / dirname).mkdir(parents=True, exist_ok=True)

    def _find_source_file(self, source_dir: Path, source_key: str) -> Optional[Path]:
        for path in sorted(source_dir.glob("*.csv")):
            if source_key in path.name:
                return path
        return None

    def _read_source(self, source_file: Path) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        with source_file.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh, delimiter="|")
            for row in reader:
                cleaned = {}
                for key, value in row.items():
                    cleaned_key = (key or "").strip()
                    cleaned[cleaned_key] = (value or "").strip()
                rows.append(cleaned)
        return rows

    def _apply_filter(self, rows: Sequence[Dict[str, str]], spec: TableSpec) -> List[Dict[str, str]]:
        return [row for row in rows if self._match_filter(row.get(spec.filter_field, ""), spec)]

    def _match_filter(self, value: str, spec: TableSpec) -> bool:
        text = (value or "").strip()
        op = spec.filter_operator
        if op == "eq":
            return text == str(spec.filter_value)
        if op == "in":
            allowed = {str(item) for item in spec.filter_value}
            return text in allowed
        if op == "non_empty":
            return text != ""
        if op == "empty":
            return text == ""
        if op == "ge_int":
            try:
                return int(float(text)) >= int(spec.filter_value)
            except ValueError:
                return False
        if op == "le_int":
            try:
                return int(float(text)) <= int(spec.filter_value)
            except ValueError:
                return False
        if op == "gt_decimal":
            try:
                return float(text) > float(spec.filter_value)
            except ValueError:
                return False
        if op == "date_ge":
            try:
                return datetime.strptime(text[:10], "%Y-%m-%d").date() >= datetime.strptime(
                    str(spec.filter_value),
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                return False
        raise ValueError(f"unsupported filter operator: {op}")

    def _select_columns(
        self,
        rows: Sequence[Dict[str, str]],
        columns: Sequence[str],
    ) -> List[Dict[str, str]]:
        selected: List[Dict[str, str]] = []
        for row in rows:
            selected.append({column: row.get(column, "") for column in columns})
        return selected

    def _drop_duplicates(self, rows: Sequence[Dict[str, str]], id_field: str) -> List[Dict[str, str]]:
        deduped: List[Dict[str, str]] = []
        seen = set()
        for row in rows:
            row_id = (row.get(id_field) or "").strip()
            if not row_id:
                continue
            if row_id in seen:
                continue
            seen.add(row_id)
            deduped.append(row)
        return deduped

    def _write_rows(
        self,
        output_path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _read_csv_rows(self, csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
        if not csv_path.exists():
            return [], []
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            rows = []
            for row in reader:
                rows.append({(key or "").strip(): (value or "").strip() for key, value in row.items()})
        return fieldnames, rows

    @staticmethod
    def _ids(rows: Sequence[Dict[str, str]]) -> set[str]:
        return {
            (row.get("id") or "").strip()
            for row in rows
            if (row.get("id") or "").strip()
        }

    def _build_text_rows(self, rows: Sequence[Dict[str, str]], spec: TableSpec) -> List[Dict[str, str]]:
        if not spec.text_fields:
            return []

        output: List[Dict[str, str]] = []
        for row in rows:
            chunks: List[str] = []
            for field in spec.text_fields:
                value = (row.get(field) or "").strip()
                if value:
                    chunks.append(f"{field}: {value}")
            if not chunks:
                continue
            row_id = (row.get(spec.id_field) or "").strip()
            if not row_id:
                continue
            row_name = (row.get(spec.name_field) or "").strip() or row_id
            output.append(
                {
                    "id": row_id,
                    "name": row_name,
                    "entity_type": spec.entity_type,
                    "text": "\n".join(chunks),
                    "source_table": spec.source_key,
                    "update_time": (row.get("update_time") or "").strip(),
                }
            )
        return output

    @staticmethod
    def _make_name_id(prefix: str, name: str) -> str:
        digest = hashlib.sha1(f"{prefix}:{name}".encode("utf-8")).hexdigest()[:20]
        return f"{prefix.upper()}_{digest}"

    @staticmethod
    def _normalize_name(value: str) -> str:
        text = (value or "").strip()
        text = text.strip("\"'[]()（）")
        text = re.sub(r"\s+", "", text)
        return text

    @staticmethod
    def _split_text_values(value: str) -> List[str]:
        text = (value or "").strip()
        if not text:
            return []
        parts = re.split(r"[;；、,/，\n]+", text)
        output: List[str] = []
        seen = set()
        for part in parts:
            item = part.strip().strip("\"'")
            if not item or len(item) < 2:
                continue
            if item in seen:
                continue
            seen.add(item)
            output.append(item)
        return output

    def _parse_array_like(self, value: str) -> List[str]:
        text = (value or "").strip()
        if not text:
            return []
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        text = text.replace('""', '"')
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                output = []
                for item in parsed:
                    cleaned = str(item).strip()
                    if cleaned:
                        output.append(cleaned)
                return output
        except Exception:
            pass
        return self._split_text_values(text)

    @staticmethod
    def _guess_org_type(name: str) -> Optional[str]:
        normalized = FactLibraryPipeline._normalize_name(name)
        if not normalized:
            return None

        company_suffixes = (
            "有限公司",
            "有限责任公司",
            "股份有限公司",
            "股份公司",
            "集团",
            "厂",
            "店",
            "事务所",
            "合伙企业",
            "公司",
        )
        institution_markers = (
            "大学",
            "学院",
            "研究院",
            "研究所",
            "科学院",
            "实验室",
            "研究中心",
            "工程中心",
            "工程实验室",
            "重点实验室",
            "医院",
            "学校",
            "学会",
            "协会",
            "图书馆",
            "博物馆",
        )

        if normalized.endswith(company_suffixes):
            return "Company"
        if any(marker in normalized for marker in institution_markers):
            return "Institution"
        return None

    def _resolve_company_reference(
        self,
        raw_name: str,
        company_index: Dict[str, str],
        valid_company_ids: set[str],
    ) -> str:
        normalized = self._normalize_name(raw_name)
        if not normalized:
            return ""
        company_id = company_index.get(normalized, "")
        if not company_id or company_id not in valid_company_ids:
            return ""
        if self._guess_org_type(raw_name) == "Institution":
            return ""
        return company_id

    def _resolve_org_reference(
        self,
        raw_name: str,
        company_index: Dict[str, str],
        institution_index: Dict[str, str],
        valid_company_ids: set[str],
        valid_institution_ids: set[str],
    ) -> tuple[str, str]:
        normalized = self._normalize_name(raw_name)
        if not normalized:
            return "", ""

        company_id = company_index.get(normalized, "")
        institution_id = institution_index.get(normalized, "")
        if company_id and company_id not in valid_company_ids:
            company_id = ""
        if institution_id and institution_id not in valid_institution_ids:
            institution_id = ""

        hint = self._guess_org_type(raw_name)
        if company_id and institution_id:
            if hint == "Company":
                return "Company", company_id
            if hint == "Institution":
                return "Institution", institution_id
            return "", ""
        if company_id:
            if hint == "Institution":
                return "", ""
            return "Company", company_id
        if institution_id:
            if hint == "Company":
                return "", ""
            return "Institution", institution_id
        return "", ""

    def _build_exact_name_index(
        self,
        rows: Sequence[Dict[str, str]],
        name_field: str = "name",
        alias_field: Optional[str] = None,
    ) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for row in rows:
            entity_id = (row.get("id") or "").strip()
            if not entity_id:
                continue
            names = []
            primary = (row.get(name_field) or "").strip()
            if primary:
                names.append(primary)
            if alias_field:
                names.extend(self._split_text_values(row.get(alias_field, "")))
            for name in names:
                normalized = self._normalize_name(name)
                if normalized and normalized not in index:
                    index[normalized] = entity_id
        return index

    def _append_relation_file(
        self,
        dataset_output: Path,
        relation_name: str,
        rows: List[Dict[str, str]],
        summary: List[Dict[str, object]],
    ) -> None:
        if rows:
            deduped_rows: List[Dict[str, str]] = []
            seen = set()
            for row in rows:
                relation_key = (
                    row.get("s_id", ""),
                    row.get("s_type", ""),
                    row.get("p", ""),
                    row.get("o_id", ""),
                    row.get("o_type", ""),
                )
                if relation_key in seen:
                    continue
                seen.add(relation_key)
                deduped_rows.append(row)
            rows = deduped_rows
        if not rows:
            return
        output_path = dataset_output / "relations" / f"{relation_name}.csv"
        self._write_rows(
            output_path,
            ("s_id", "s_type", "p", "o_id", "o_type", "properties"),
            rows,
        )
        summary.append(
            {
                "name": relation_name,
                "rows": len(rows),
                "output_path": str(output_path),
            }
        )

    def _export_derived_entities(
        self,
        dataset_output: Path,
        filtered_rows_by_source: Dict[str, List[Dict[str, str]]],
    ) -> List[Dict[str, object]]:
        summaries: List[Dict[str, object]] = []
        support_rows = filtered_rows_by_source.get("dw_company_main_product", [])
        valid_company_ids = self._ids(filtered_rows_by_source.get("dw_company_info_tyc", []))
        seen_products = set()
        product_rows: List[Dict[str, str]] = []
        for row in support_rows:
            if (row.get("id") or "").strip() not in valid_company_ids:
                continue
            for product_name in self._split_text_values(row.get("main_product", "")):
                normalized = self._normalize_name(product_name)
                if not normalized or normalized in seen_products:
                    continue
                seen_products.add(normalized)
                product_rows.append(
                    {
                        "id": self._make_name_id("product", normalized),
                        "name": product_name,
                        "desc": "",
                        "semanticType": "Product",
                    }
                )
        if product_rows:
            output_path = dataset_output / "entities" / "product.csv"
            self._write_rows(output_path, ("id", "name", "desc", "semanticType"), product_rows)
            filtered_rows_by_source["_derived_product"] = product_rows
            summaries.append(
                {
                    "source_key": "_derived_product",
                    "source_file": "generated",
                    "output_group": "entities",
                    "output_name": "product",
                    "entity_type": "Product",
                    "filter_rule": "derived from company_main_product.main_product",
                    "total_rows": len(product_rows),
                    "kept_rows": len(product_rows),
                    "dropped_rows": 0,
                    "output_path": str(output_path),
                    "text_path": "",
                    "status": "ok",
                }
            )
        return summaries

    def _export_relations(
        self,
        dataset_output: Path,
        filtered_rows_by_source: Dict[str, List[Dict[str, str]]],
    ) -> List[Dict[str, object]]:
        summary: List[Dict[str, object]] = []
        unmatched_names: Dict[str, Counter[str]] = defaultdict(Counter)
        relation_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"candidate_count": 0, "matched_count": 0, "unmatched_count": 0}
        )
        company_index = self._build_exact_name_index(
            filtered_rows_by_source.get("dw_company_info_tyc", []),
            name_field="name",
            alias_field="used_name",
        )
        institution_index = self._build_exact_name_index(
            filtered_rows_by_source.get("dw_institution_2026", []),
            name_field="name",
        )
        person_index = self._build_exact_name_index(
            filtered_rows_by_source.get("dw_expert", []),
            name_field="name",
        )
        product_index = self._build_exact_name_index(
            filtered_rows_by_source.get("_derived_product", []),
            name_field="name",
        )
        valid_company_ids = self._ids(filtered_rows_by_source.get("dw_company_info_tyc", []))
        valid_institution_ids = self._ids(filtered_rows_by_source.get("dw_institution_2026", []))
        valid_person_ids = self._ids(filtered_rows_by_source.get("dw_expert", []))
        valid_product_ids = self._ids(filtered_rows_by_source.get("_derived_product", []))
        valid_ranking_list_ids = self._ids(filtered_rows_by_source.get("dw_list", []))

        def track_match(bucket: str, raw_name: str, matched: bool) -> None:
            cleaned = (raw_name or "").strip()
            relation_stats[bucket]["candidate_count"] += 1
            if matched:
                relation_stats[bucket]["matched_count"] += 1
            else:
                relation_stats[bucket]["unmatched_count"] += 1
                if cleaned:
                    unmatched_names[bucket][cleaned] += 1

        institution_rows = filtered_rows_by_source.get("dw_institution_2026", [])
        rel_rows: List[Dict[str, str]] = []
        for row in institution_rows:
            support_org_id = (row.get("support_org_id") or "").strip()
            target_company_id = support_org_id
            if target_company_id and target_company_id not in valid_company_ids:
                target_company_id = ""
            if target_company_id:
                track_match("institution_supported_by_company", support_org_id, True)
                rel_rows.append(
                    {
                        "s_id": (row.get("id") or "").strip(),
                        "s_type": "Institution",
                        "p": "supportedBy",
                        "o_id": target_company_id,
                        "o_type": "Company",
                        "properties": json.dumps(
                            {
                                "support_org_name": (row.get("support_org_name") or "").strip(),
                                "update_time": (row.get("update_time") or "").strip(),
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
                continue
            for candidate in self._split_text_values(row.get("support_org_name", "")):
                target_company_id = self._resolve_company_reference(
                    candidate,
                    company_index,
                    valid_company_ids,
                )
                track_match("institution_supported_by_company", candidate, bool(target_company_id))
                if not target_company_id:
                    continue
                rel_rows.append(
                    {
                        "s_id": (row.get("id") or "").strip(),
                        "s_type": "Institution",
                        "p": "supportedBy",
                        "o_id": target_company_id,
                        "o_type": "Company",
                        "properties": json.dumps(
                            {
                                "support_org_name": candidate,
                                "update_time": (row.get("update_time") or "").strip(),
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
        self._append_relation_file(dataset_output, "institution_supported_by_company", rel_rows, summary)

        list_detail_rows = filtered_rows_by_source.get("dw_list_detail", [])
        rel_rows = []
        for row in list_detail_rows:
            company_id = (row.get("cid") or "").strip()
            ranking_list_id = (row.get("pid") or "").strip()
            if not company_id or company_id not in valid_company_ids:
                track_match("ranking_list_includes_company", row.get("company_name", ""), False)
                continue
            if not ranking_list_id or ranking_list_id not in valid_ranking_list_ids:
                continue
            track_match("ranking_list_includes_company", row.get("company_name", ""), True)
            rel_rows.append(
                {
                    "s_id": ranking_list_id,
                    "s_type": "RankingList",
                    "p": "includesCompany",
                    "o_id": company_id,
                    "o_type": "Company",
                    "properties": json.dumps(
                        {
                            "sort_order": (row.get("sort_order") or "").strip(),
                            "company_name": (row.get("company_name") or "").strip(),
                            "update_time": (row.get("update_time") or "").strip(),
                        },
                        ensure_ascii=False,
                    ),
                }
            )
        self._append_relation_file(dataset_output, "ranking_list_includes_company", rel_rows, summary)

        company_product_rows = filtered_rows_by_source.get("dw_company_main_product", [])
        rel_rows = []
        for row in company_product_rows:
            company_id = (row.get("id") or "").strip()
            if not company_id or company_id not in valid_company_ids:
                continue
            for product_name in self._split_text_values(row.get("main_product", "")):
                product_id = product_index.get(self._normalize_name(product_name), "")
                matched = bool(product_id and product_id in valid_product_ids)
                track_match("company_has_main_product", product_name, matched)
                if not matched:
                    continue
                rel_rows.append(
                    {
                        "s_id": company_id,
                        "s_type": "Company",
                        "p": "hasMainProduct",
                        "o_id": product_id,
                        "o_type": "Product",
                        "properties": json.dumps(
                            {
                                "product_name": product_name,
                                "update_time": (row.get("update_time") or "").strip(),
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
        self._append_relation_file(dataset_output, "company_has_main_product", rel_rows, summary)

        patent_rows = filtered_rows_by_source.get("dw_patent_china", [])
        patent_company_apply_rows: List[Dict[str, str]] = []
        patent_institution_apply_rows: List[Dict[str, str]] = []
        patent_company_owner_rows: List[Dict[str, str]] = []
        patent_institution_owner_rows: List[Dict[str, str]] = []
        patent_inventor_rows: List[Dict[str, str]] = []
        for row in patent_rows:
            patent_id = (row.get("id") or "").strip()
            if not patent_id:
                continue
            for applicant in self._parse_array_like(row.get("applicants_norm", "")):
                target_type, target_id = self._resolve_org_reference(
                    applicant,
                    company_index,
                    institution_index,
                    valid_company_ids,
                    valid_institution_ids,
                )
                track_match("patent_applicants", applicant, bool(target_id))
                if target_type == "Company":
                    patent_company_apply_rows.append(
                        {
                            "s_id": patent_id,
                            "s_type": "Patent",
                            "p": "appliedByCompany",
                            "o_id": target_id,
                            "o_type": "Company",
                            "properties": json.dumps({"matched_name": applicant}, ensure_ascii=False),
                        }
                    )
                elif target_type == "Institution":
                    patent_institution_apply_rows.append(
                        {
                            "s_id": patent_id,
                            "s_type": "Patent",
                            "p": "appliedByInstitution",
                            "o_id": target_id,
                            "o_type": "Institution",
                            "properties": json.dumps({"matched_name": applicant}, ensure_ascii=False),
                        }
                    )
            for owner in self._parse_array_like(row.get("patentees_norm", "")):
                target_type, target_id = self._resolve_org_reference(
                    owner,
                    company_index,
                    institution_index,
                    valid_company_ids,
                    valid_institution_ids,
                )
                track_match("patent_owners", owner, bool(target_id))
                if target_type == "Company":
                    patent_company_owner_rows.append(
                        {
                            "s_id": patent_id,
                            "s_type": "Patent",
                            "p": "ownedByCompany",
                            "o_id": target_id,
                            "o_type": "Company",
                            "properties": json.dumps({"matched_name": owner}, ensure_ascii=False),
                        }
                    )
                elif target_type == "Institution":
                    patent_institution_owner_rows.append(
                        {
                            "s_id": patent_id,
                            "s_type": "Patent",
                            "p": "ownedByInstitution",
                            "o_id": target_id,
                            "o_type": "Institution",
                            "properties": json.dumps({"matched_name": owner}, ensure_ascii=False),
                        }
                    )
            for inventor in self._parse_array_like(row.get("inventors", "")):
                person_id = person_index.get(self._normalize_name(inventor), "")
                matched = bool(person_id and person_id in valid_person_ids)
                track_match("patent_inventors", inventor, matched)
                if not matched:
                    continue
                patent_inventor_rows.append(
                    {
                        "s_id": patent_id,
                        "s_type": "Patent",
                        "p": "inventedBy",
                        "o_id": person_id,
                        "o_type": "Person",
                        "properties": json.dumps({"matched_name": inventor}, ensure_ascii=False),
                    }
                )
        self._append_relation_file(dataset_output, "patent_applied_by_company", patent_company_apply_rows, summary)
        self._append_relation_file(dataset_output, "patent_applied_by_institution", patent_institution_apply_rows, summary)
        self._append_relation_file(dataset_output, "patent_owned_by_company", patent_company_owner_rows, summary)
        self._append_relation_file(dataset_output, "patent_owned_by_institution", patent_institution_owner_rows, summary)
        self._append_relation_file(dataset_output, "patent_invented_by_person", patent_inventor_rows, summary)

        project_rows = filtered_rows_by_source.get("dw_project", [])
        project_leader_rows: List[Dict[str, str]] = []
        project_company_rows: List[Dict[str, str]] = []
        project_institution_rows: List[Dict[str, str]] = []
        for row in project_rows:
            project_id = (row.get("id") or "").strip()
            if not project_id:
                continue
            leader_name = (row.get("project_leader") or "").strip()
            leader_id = person_index.get(self._normalize_name(leader_name), "")
            leader_matched = bool(leader_id and leader_id in valid_person_ids)
            track_match("project_leader", leader_name, leader_matched)
            if leader_matched:
                project_leader_rows.append(
                    {
                        "s_id": project_id,
                        "s_type": "Project",
                        "p": "ledBy",
                        "o_id": leader_id,
                        "o_type": "Person",
                        "properties": json.dumps({"matched_name": leader_name}, ensure_ascii=False),
                    }
                )
            for org_name in self._split_text_values(row.get("org", "")):
                target_type, target_id = self._resolve_org_reference(
                    org_name,
                    company_index,
                    institution_index,
                    valid_company_ids,
                    valid_institution_ids,
                )
                track_match("project_org", org_name, bool(target_id))
                if target_type == "Company":
                    project_company_rows.append(
                        {
                            "s_id": project_id,
                            "s_type": "Project",
                            "p": "undertakenByCompany",
                            "o_id": target_id,
                            "o_type": "Company",
                            "properties": json.dumps({"matched_name": org_name}, ensure_ascii=False),
                        }
                    )
                elif target_type == "Institution":
                    project_institution_rows.append(
                        {
                            "s_id": project_id,
                            "s_type": "Project",
                            "p": "undertakenByInstitution",
                            "o_id": target_id,
                            "o_type": "Institution",
                            "properties": json.dumps({"matched_name": org_name}, ensure_ascii=False),
                        }
                    )
        self._append_relation_file(dataset_output, "project_led_by_person", project_leader_rows, summary)
        self._append_relation_file(dataset_output, "project_undertaken_by_company", project_company_rows, summary)
        self._append_relation_file(dataset_output, "project_undertaken_by_institution", project_institution_rows, summary)

        achievement_rows = filtered_rows_by_source.get("dw_achievement_info", [])
        achievement_company_rows: List[Dict[str, str]] = []
        achievement_institution_rows: List[Dict[str, str]] = []
        achievement_person_rows: List[Dict[str, str]] = []
        for row in achievement_rows:
            achievement_id = (row.get("id") or "").strip()
            if not achievement_id:
                continue
            for unit_name in self._split_text_values(row.get("unit", "")):
                target_type, target_id = self._resolve_org_reference(
                    unit_name,
                    company_index,
                    institution_index,
                    valid_company_ids,
                    valid_institution_ids,
                )
                track_match("achievement_unit", unit_name, bool(target_id))
                if target_type == "Company":
                    achievement_company_rows.append(
                        {
                            "s_id": achievement_id,
                            "s_type": "Achievement",
                            "p": "completedByCompany",
                            "o_id": target_id,
                            "o_type": "Company",
                            "properties": json.dumps({"matched_name": unit_name}, ensure_ascii=False),
                        }
                    )
                elif target_type == "Institution":
                    achievement_institution_rows.append(
                        {
                            "s_id": achievement_id,
                            "s_type": "Achievement",
                            "p": "completedByInstitution",
                            "o_id": target_id,
                            "o_type": "Institution",
                            "properties": json.dumps({"matched_name": unit_name}, ensure_ascii=False),
                        }
                    )
            for person_name in self._split_text_values(row.get("person", "")):
                person_id = person_index.get(self._normalize_name(person_name), "")
                matched = bool(person_id and person_id in valid_person_ids)
                track_match("achievement_person", person_name, matched)
                if not matched:
                    continue
                achievement_person_rows.append(
                    {
                        "s_id": achievement_id,
                        "s_type": "Achievement",
                        "p": "completedByPerson",
                        "o_id": person_id,
                        "o_type": "Person",
                        "properties": json.dumps({"matched_name": person_name}, ensure_ascii=False),
                    }
                )
        self._append_relation_file(dataset_output, "achievement_completed_by_company", achievement_company_rows, summary)
        self._append_relation_file(dataset_output, "achievement_completed_by_institution", achievement_institution_rows, summary)
        self._append_relation_file(dataset_output, "achievement_completed_by_person", achievement_person_rows, summary)

        article_rows = filtered_rows_by_source.get("dw_article", [])
        article_author_rows: List[Dict[str, str]] = []
        article_company_rows: List[Dict[str, str]] = []
        article_institution_rows: List[Dict[str, str]] = []
        for row in article_rows:
            article_id = (row.get("id") or "").strip()
            if not article_id:
                continue
            for author in self._split_text_values(row.get("authors", "")):
                person_id = person_index.get(self._normalize_name(author), "")
                matched = bool(person_id and person_id in valid_person_ids)
                track_match("article_authors", author, matched)
                if not matched:
                    continue
                article_author_rows.append(
                    {
                        "s_id": article_id,
                        "s_type": "Article",
                        "p": "authoredBy",
                        "o_id": person_id,
                        "o_type": "Person",
                        "properties": json.dumps({"matched_name": author}, ensure_ascii=False),
                    }
                )
            for applicant in self._split_text_values(row.get("applicants", "")):
                target_type, target_id = self._resolve_org_reference(
                    applicant,
                    company_index,
                    institution_index,
                    valid_company_ids,
                    valid_institution_ids,
                )
                track_match("article_applicants", applicant, bool(target_id))
                if target_type == "Company":
                    article_company_rows.append(
                        {
                            "s_id": article_id,
                            "s_type": "Article",
                            "p": "publishedByCompany",
                            "o_id": target_id,
                            "o_type": "Company",
                            "properties": json.dumps({"matched_name": applicant}, ensure_ascii=False),
                        }
                    )
                elif target_type == "Institution":
                    article_institution_rows.append(
                        {
                            "s_id": article_id,
                            "s_type": "Article",
                            "p": "publishedByInstitution",
                            "o_id": target_id,
                            "o_type": "Institution",
                            "properties": json.dumps({"matched_name": applicant}, ensure_ascii=False),
                        }
                    )
        self._append_relation_file(dataset_output, "article_authored_by_person", article_author_rows, summary)
        self._append_relation_file(dataset_output, "article_published_by_company", article_company_rows, summary)
        self._append_relation_file(dataset_output, "article_published_by_institution", article_institution_rows, summary)

        self._write_relation_stats(dataset_output, summary, relation_stats)
        self._write_unmatched_report(dataset_output, unmatched_names)

        return summary

    def _compact_quick_dataset(
        self,
        dataset_output: Path,
        tables_summary: List[Dict[str, object]],
        relation_summary: List[Dict[str, object]],
    ) -> List[Dict[str, object]]:
        degree_by_type: Dict[str, Counter[str]] = defaultdict(Counter)
        relation_rows_by_name: Dict[str, List[Dict[str, str]]] = {}
        relation_fieldnames_by_name: Dict[str, List[str]] = {}

        for item in relation_summary:
            relation_name = str(item.get("name") or "")
            output_path = Path(str(item.get("output_path") or ""))
            fieldnames, rows = self._read_csv_rows(output_path)
            relation_rows_by_name[relation_name] = rows
            relation_fieldnames_by_name[relation_name] = fieldnames
            for row in rows:
                s_id = (row.get("s_id") or "").strip()
                s_type = (row.get("s_type") or "").strip()
                o_id = (row.get("o_id") or "").strip()
                o_type = (row.get("o_type") or "").strip()
                if s_id and s_type:
                    degree_by_type[s_type][s_id] += 1
                if o_id and o_type:
                    degree_by_type[o_type][o_id] += 1

        keep_ids_by_type: Dict[str, set[str]] = {}
        for entity_type, counter in degree_by_type.items():
            limit = QUICK_ENTITY_LIMITS.get(entity_type, 0)
            if limit <= 0:
                keep_ids_by_type[entity_type] = set()
                continue
            keep_ids_by_type[entity_type] = {
                entity_id for entity_id, _ in counter.most_common(limit)
            }

        active_ids_by_type: Dict[str, set[str]] = defaultdict(set)
        filtered_relation_summary: List[Dict[str, object]] = []
        for item in relation_summary:
            relation_name = str(item.get("name") or "")
            output_path = Path(str(item.get("output_path") or ""))
            fieldnames = relation_fieldnames_by_name.get(relation_name) or [
                "s_id",
                "s_type",
                "p",
                "o_id",
                "o_type",
                "properties",
            ]
            rows = relation_rows_by_name.get(relation_name, [])
            kept_rows: List[Dict[str, str]] = []
            for row in rows:
                s_id = (row.get("s_id") or "").strip()
                s_type = (row.get("s_type") or "").strip()
                o_id = (row.get("o_id") or "").strip()
                o_type = (row.get("o_type") or "").strip()
                if s_id not in keep_ids_by_type.get(s_type, set()):
                    continue
                if o_id not in keep_ids_by_type.get(o_type, set()):
                    continue
                kept_rows.append(row)
                active_ids_by_type[s_type].add(s_id)
                active_ids_by_type[o_type].add(o_id)
            self._write_rows(output_path, fieldnames, kept_rows)
            if kept_rows:
                new_item = dict(item)
                new_item["rows"] = len(kept_rows)
                filtered_relation_summary.append(new_item)

        for item in tables_summary:
            if item.get("output_group") != "entities":
                continue
            entity_type = str(item.get("entity_type") or "")
            keep_ids = active_ids_by_type.get(entity_type, set())
            output_path = Path(str(item.get("output_path") or ""))
            fieldnames, rows = self._read_csv_rows(output_path)
            kept_rows = [
                row
                for row in rows
                if (row.get("id") or "").strip() in keep_ids
            ]
            self._write_rows(output_path, fieldnames, kept_rows)
            item["kept_rows"] = len(kept_rows)
            item["dropped_rows"] = max(int(item.get("total_rows") or 0) - len(kept_rows), 0)

            text_path_value = str(item.get("text_path") or "")
            if text_path_value:
                text_path = Path(text_path_value)
                text_fieldnames, text_rows = self._read_csv_rows(text_path)
                kept_text_rows = [
                    row
                    for row in text_rows
                    if (row.get("id") or "").strip() in keep_ids
                ]
                if text_fieldnames:
                    self._write_rows(text_path, text_fieldnames, kept_text_rows)

        return filtered_relation_summary

    def _refresh_relation_summary_output_rows(
        self,
        dataset_output: Path,
        relation_summary: Sequence[Dict[str, object]],
    ) -> None:
        summary_path = dataset_output / "stats" / "relation_summary.csv"
        fieldnames, rows = self._read_csv_rows(summary_path)
        if not fieldnames or not rows:
            return
        output_rows_by_name = {
            str(row.get("name") or ""): int(row.get("rows") or 0)
            for row in relation_summary
        }
        refreshed_rows: List[Dict[str, str]] = []
        for row in rows:
            bucket = str(row.get("bucket") or "")
            output_rows = sum(
                output_rows_by_name.get(name, 0)
                for name in self.RELATION_OUTPUT_GROUPS.get(bucket, ())
            )
            row["output_rows"] = str(output_rows)
            refreshed_rows.append(row)
        self._write_rows(summary_path, fieldnames, refreshed_rows)

    def _write_summary(self, summary_path: Path, rows: Sequence[Dict[str, object]]) -> None:
        fieldnames = [
            "source_key",
            "source_file",
            "output_group",
            "output_name",
            "entity_type",
            "filter_rule",
            "total_rows",
            "kept_rows",
            "dropped_rows",
            "output_path",
            "text_path",
            "status",
        ]
        with summary_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _write_relation_stats(
        self,
        dataset_output: Path,
        relation_rows: Sequence[Dict[str, object]],
        relation_stats: Dict[str, Dict[str, int]],
    ) -> None:
        output_path = dataset_output / "stats" / "relation_summary.csv"
        fieldnames = [
            "bucket",
            "candidate_count",
            "matched_count",
            "unmatched_count",
            "output_rows",
        ]
        output_rows_by_name = {
            str(row.get("name") or ""): int(row.get("rows") or 0)
            for row in relation_rows
        }
        rows = []
        for bucket in sorted(relation_stats):
            item = relation_stats[bucket]
            output_rows = sum(
                output_rows_by_name.get(name, 0)
                for name in self.RELATION_OUTPUT_GROUPS.get(bucket, ())
            )
            rows.append(
                {
                    "bucket": bucket,
                    "candidate_count": item["candidate_count"],
                    "matched_count": item["matched_count"],
                    "unmatched_count": item["unmatched_count"],
                    "output_rows": output_rows,
                }
            )
        self._write_rows(output_path, fieldnames, rows)

    def _write_unmatched_report(
        self,
        dataset_output: Path,
        unmatched_names: Dict[str, Counter[str]],
    ) -> None:
        output_path = dataset_output / "stats" / "unmatched_relation_candidates.csv"
        rows: List[Dict[str, str]] = []
        for bucket, counter in sorted(unmatched_names.items()):
            for raw_name, count in counter.most_common():
                rows.append(
                    {
                        "bucket": bucket,
                        "raw_name": raw_name,
                        "count": str(count),
                    }
                )
        self._write_rows(output_path, ("bucket", "raw_name", "count"), rows)
