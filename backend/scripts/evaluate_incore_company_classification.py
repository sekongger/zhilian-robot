"""Evaluate company concept classification on fact-library company samples."""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from app.incore_fusion_pipeline.taxonomy import COMPANY_CATEGORY_PARENT_MAP, CompanyConceptClassifier


ACTIVE_STATUSES = {"存续", "在业", "正常"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IncCore company concept classification.")
    parser.add_argument(
        "--input",
        default="/Users/caixudong/Downloads/zhilian-robot/backend/data/fact_library/raw/20260313_183538/lz_dw_knowledge_center.dw_company_info_tyc_20260313_183538_top50000.csv",
        help="Input company CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default="/Users/caixudong/Downloads/zhilian-robot/docs/reports/assets/incore_company_classification_eval",
        help="Directory for generated CSV/SVG assets.",
    )
    parser.add_argument(
        "--report",
        default="/Users/caixudong/Downloads/zhilian-robot/docs/reports/2026-03-22-incore-company-classification-eval.md",
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max active rows to evaluate. 0 means all.",
    )
    return parser.parse_args()


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_svg_bar_chart(path: Path, title: str, rows: List[Tuple[str, int]], *, width: int = 1100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        return
    margin_left = 260
    margin_top = 60
    bar_height = 28
    row_gap = 12
    chart_width = width - margin_left - 120
    max_value = max(value for _, value in rows) or 1
    height = margin_top + len(rows) * (bar_height + row_gap) + 60
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>",
        "<style>text{font-family:Arial,'PingFang SC','Microsoft YaHei',sans-serif;fill:#243447;} .title{font-size:26px;font-weight:700;} .label{font-size:16px;} .value{font-size:15px;fill:#4b5d73;} .bar{fill:#4f7cf7;} .grid{stroke:#dbe4f0;stroke-width:1;} </style>",
        f"<text x='40' y='36' class='title'>{html.escape(title)}</text>",
    ]
    for index, (label, value) in enumerate(rows):
        y = margin_top + index * (bar_height + row_gap)
        bar_width = int(chart_width * (value / max_value))
        parts.append(f"<line x1='{margin_left}' y1='{y + bar_height / 2}' x2='{margin_left + chart_width}' y2='{y + bar_height / 2}' class='grid' />")
        parts.append(f"<text x='{margin_left - 10}' y='{y + 20}' text-anchor='end' class='label'>{html.escape(label)}</text>")
        parts.append(f"<rect x='{margin_left}' y='{y}' width='{bar_width}' height='{bar_height}' rx='6' class='bar' />")
        parts.append(f"<text x='{margin_left + bar_width + 10}' y='{y + 20}' class='value'>{value}</text>")
    parts.append("</svg>")
    path.write_text("".join(parts), encoding="utf-8")


def aggregate_parent_categories(counter: Counter) -> Counter:
    parent_counter: Counter = Counter()
    for category, count in counter.items():
        parent = COMPANY_CATEGORY_PARENT_MAP.get(category, category)
        parent_counter[parent] += count
    return parent_counter


def build_examples_by_category(rows: List[Dict[str, object]], limit_per_category: int = 5) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        categories = str(row["company_categories"]).split(" | ") if row["company_categories"] else []
        for category in categories:
            if category and len(grouped[category]) < limit_per_category:
                grouped[category].append(row)
    result: List[Dict[str, object]] = []
    for category, items in sorted(grouped.items()):
        for item in items:
            result.append(
                {
                    "category": category,
                    "name": item["name"],
                    "business_scope": item["business_scope"],
                    "company_categories": item["company_categories"],
                    "industry_sectors": item["industry_sectors"],
                }
            )
    return result


def write_report(
    path: Path,
    *,
    summary: Dict[str, object],
    category_distribution_path: Path,
    parent_distribution_path: Path,
    industry_distribution_path: Path,
    category_chart_path: Path,
    parent_chart_path: Path,
    industry_chart_path: Path,
    predictions_path: Path,
    uncategorized_path: Path,
    examples_path: Path,
) -> None:
    top_categories = summary["top_company_categories"]
    top_parents = summary["top_parent_categories"]
    top_industries = summary["top_industry_sectors"]
    lines = [
        "# IncCore 企业概念分类评估",
        "",
        "## 1. 评估目的",
        "",
        "- 验证当前增强后的概念层，是否已经具备对企业实体进行自动分类的能力。",
        "- 重点观察企业分类覆盖率、主要分类分布，以及行业分类分布是否符合直觉。",
        "- 当前评估属于规则覆盖率与结果分布评估，不是带人工标注真值的精确率/召回率评测。",
        "",
        "## 2. 评估数据",
        "",
        f"- 输入文件：[dw_company_info_tyc_top50000]({summary['input_path']})",
        f"- 评估活跃企业数：`{summary['evaluated_active_companies']}`",
        "- 活跃企业口径：`status in {存续, 在业, 正常}`",
        "",
        "## 3. 核心结果",
        "",
        f"- 企业分类覆盖率：`{summary['company_category_coverage']}`",
        f"- 行业分类覆盖率：`{summary['industry_coverage']}`",
        f"- 平均每家企业命中的企业分类数：`{summary['avg_company_categories_per_company']}`",
        f"- 平均每家企业命中的行业分类数：`{summary['avg_industries_per_company']}`",
        "",
        "## 4. 企业分类 Top 分布",
        "",
        f"- 明细表：[company_category_distribution.csv]({category_distribution_path})",
        f"- 图表：[company_category_distribution.svg]({category_chart_path})",
        "",
        f"![企业分类分布]({category_chart_path})",
        "",
        "| 分类 | 数量 |",
        "|---|---:|",
        *[f"| {name} | {count} |" for name, count in top_categories],
        "",
        "## 5. 企业一级父类 Top 分布",
        "",
        f"- 明细表：[company_category_parent_distribution.csv]({parent_distribution_path})",
        f"- 图表：[company_category_parent_distribution.svg]({parent_chart_path})",
        "",
        f"![企业一级父类分布]({parent_chart_path})",
        "",
        "| 一级分类 | 数量 |",
        "|---|---:|",
        *[f"| {name} | {count} |" for name, count in top_parents],
        "",
        "## 6. 行业分类 Top 分布",
        "",
        f"- 明细表：[industry_sector_distribution.csv]({industry_distribution_path})",
        f"- 图表：[industry_sector_distribution.svg]({industry_chart_path})",
        "",
        f"![行业分类分布]({industry_chart_path})",
        "",
        "| 行业 | 数量 |",
        "|---|---:|",
        *[f"| {name} | {count} |" for name, count in top_industries],
        "",
        "## 7. 结果文件",
        "",
        f"- 全量预测结果：[company_classification_predictions.csv]({predictions_path})",
        f"- 未分类样本：[company_classification_uncategorized.csv]({uncategorized_path})",
        f"- 各分类样例：[company_classification_examples.csv]({examples_path})",
        "",
        "## 8. 结论",
        "",
        "- 当前概念层已经不再只是“抽象概念节点存储”，而是具备了实际的企业分类能力。",
        "- 企业分类已经可以稳定产出 `Company -> category -> CompanyCategory` 以及 `Company -> industry -> IndustrySector` 两类关系。",
        "- 现阶段最强的是对商贸、科技、工程建设、农业食品、制造、企业服务类企业的识别。",
        "- 下一步可继续补强两类能力：",
        "  - 用更多结构化字段提升分类精度，例如注册资本、参保人数、行业编码、主营产品。",
        "  - 在资讯/研报抽取链中，把事件主体企业的分类结果反向写回，提升事件层的概念绑定质量。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)
    classifier = CompanyConceptClassifier()

    predictions_rows: List[Dict[str, object]] = []
    uncategorized_rows: List[Dict[str, object]] = []
    company_category_counter: Counter = Counter()
    industry_counter: Counter = Counter()
    evaluated_active = 0
    company_category_hits = 0
    industry_hits = 0
    total_company_category_count = 0
    total_industry_count = 0

    with input_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            if row.get("status") not in ACTIVE_STATUSES:
                continue
            evaluated_active += 1
            result = classifier.classify_company(
                name=row.get("name", ""),
                business_scope=row.get("business_scope", ""),
                description=row.get("description", ""),
            )
            company_categories = result["company_categories"]
            industries = result["industry_sectors"]
            if company_categories:
                company_category_hits += 1
                total_company_category_count += len(company_categories)
                for predicted in company_categories:
                    company_category_counter[predicted.concept_name] += 1
            else:
                uncategorized_rows.append(
                    {
                        "id": row.get("id", ""),
                        "name": row.get("name", ""),
                        "credit_code": row.get("credit_code", ""),
                        "status": row.get("status", ""),
                        "business_scope": row.get("business_scope", ""),
                    }
                )
            if industries:
                industry_hits += 1
                total_industry_count += len(industries)
                for predicted in industries:
                    industry_counter[predicted.concept_name] += 1

            predictions_rows.append(
                {
                    "id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "credit_code": row.get("credit_code", ""),
                    "status": row.get("status", ""),
                    "province": row.get("province", ""),
                    "city": row.get("city", ""),
                    "company_categories": " | ".join(item.concept_name for item in company_categories),
                    "company_category_scores": " | ".join(f"{item.concept_name}:{item.score}" for item in company_categories),
                    "industry_sectors": " | ".join(item.concept_name for item in industries),
                    "industry_scores": " | ".join(f"{item.concept_name}:{item.score}" for item in industries),
                    "business_scope": row.get("business_scope", ""),
                }
            )
            if args.limit and evaluated_active >= args.limit:
                break

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "company_classification_predictions.csv"
    uncategorized_path = output_dir / "company_classification_uncategorized.csv"
    examples_path = output_dir / "company_classification_examples.csv"
    category_distribution_path = output_dir / "company_category_distribution.csv"
    parent_distribution_path = output_dir / "company_category_parent_distribution.csv"
    industry_distribution_path = output_dir / "industry_sector_distribution.csv"
    category_chart_path = output_dir / "company_category_distribution.svg"
    parent_chart_path = output_dir / "company_category_parent_distribution.svg"
    industry_chart_path = output_dir / "industry_sector_distribution.svg"
    summary_path = output_dir / "coverage_summary.json"

    write_csv(
        predictions_path,
        predictions_rows,
        [
            "id",
            "name",
            "credit_code",
            "status",
            "province",
            "city",
            "company_categories",
            "company_category_scores",
            "industry_sectors",
            "industry_scores",
            "business_scope",
        ],
    )
    write_csv(
        uncategorized_path,
        uncategorized_rows[:500],
        ["id", "name", "credit_code", "status", "business_scope"],
    )
    write_csv(
        category_distribution_path,
        [{"category": name, "count": count} for name, count in company_category_counter.most_common()],
        ["category", "count"],
    )
    parent_counter = aggregate_parent_categories(company_category_counter)
    write_csv(
        parent_distribution_path,
        [{"parent_category": name, "count": count} for name, count in parent_counter.most_common()],
        ["parent_category", "count"],
    )
    write_csv(
        industry_distribution_path,
        [{"industry_sector": name, "count": count} for name, count in industry_counter.most_common()],
        ["industry_sector", "count"],
    )
    examples_rows = build_examples_by_category(predictions_rows)
    write_csv(
        examples_path,
        examples_rows,
        ["category", "name", "business_scope", "company_categories", "industry_sectors"],
    )

    write_svg_bar_chart(category_chart_path, "企业细分类分布（Top 12）", company_category_counter.most_common(12))
    write_svg_bar_chart(parent_chart_path, "企业一级父类分布（Top 10）", parent_counter.most_common(10))
    write_svg_bar_chart(industry_chart_path, "行业分类分布（Top 12）", industry_counter.most_common(12))

    summary = {
        "input_path": str(input_path),
        "evaluated_active_companies": evaluated_active,
        "company_category_coverage": round(company_category_hits / evaluated_active, 4) if evaluated_active else 0.0,
        "industry_coverage": round(industry_hits / evaluated_active, 4) if evaluated_active else 0.0,
        "avg_company_categories_per_company": round(total_company_category_count / company_category_hits, 4) if company_category_hits else 0.0,
        "avg_industries_per_company": round(total_industry_count / industry_hits, 4) if industry_hits else 0.0,
        "top_company_categories": company_category_counter.most_common(12),
        "top_parent_categories": parent_counter.most_common(10),
        "top_industry_sectors": industry_counter.most_common(12),
        "uncategorized_sample_count": len(uncategorized_rows),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    write_report(
        report_path,
        summary=summary,
        category_distribution_path=category_distribution_path,
        parent_distribution_path=parent_distribution_path,
        industry_distribution_path=industry_distribution_path,
        category_chart_path=category_chart_path,
        parent_chart_path=parent_chart_path,
        industry_chart_path=industry_chart_path,
        predictions_path=predictions_path,
        uncategorized_path=uncategorized_path,
        examples_path=examples_path,
    )
    print(json.dumps({"summary": summary, "report": str(report_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
