from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SeedModule:
    name: str
    title: str
    stage: str
    owner: str
    path: str
    summary: str
    dependencies: tuple[str, ...] = ()


SEED_MODULES = [
    SeedModule("base_kg", "产业网链基础", "fact", "蔡旭东、陆文韬", "openks/kg/fact/base_kg", "定义产业网链基础、统一 ID 规则和常用实体。"),
    SeedModule("encyclopedia_kg", "百科知识库", "fact", "杨辰", "openks/kg/fact/encyclopedia_kg", "补充通用实体背景知识和百科语义。"),
    SeedModule("news_kg", "资讯知识库", "fact", "楼彦炜", "openks/kg/fact/news_kg", "提取资讯事实、事件与热点信号。", ("base_kg",)),
    SeedModule("report_kg", "研报知识库", "fact", "李奕君", "openks/kg/fact/report_kg", "抽取研报观点、结论、指标与覆盖关系。", ("base_kg",)),
    SeedModule("enterprise_kg", "企业知识库", "fact", "陆文韬", "openks/kg/fact/enterprise_kg", "沉淀企业画像、上下游和经营要素。", ("base_kg",)),
    SeedModule("policy_kg", "政策知识库", "fact", "陆文韬", "openks/kg/fact/policy_kg", "抽取政策主体、扶持方向和影响对象。", ("base_kg",)),
    SeedModule("patent_kg", "专利知识库", "fact", "林辉", "openks/kg/fact/patent_kg", "提取专利主体、技术方向和关联技术。", ("base_kg",)),
    SeedModule("organization_kg", "机构知识库", "fact", "林辉", "openks/kg/fact/organization_kg", "沉淀机构、园区、联盟和组织协同关系。", ("base_kg",)),
    SeedModule("technology_kg", "技术知识库", "fact", "林辉", "openks/kg/fact/technology_kg", "整理技术路线、成熟度和能力依赖。", ("base_kg",)),
    SeedModule("product_kg", "产品知识库", "fact", "雅馨", "openks/kg/fact/product_kg", "沉淀产品谱系、规格能力和应用场景。", ("base_kg",)),
    SeedModule("industry_chain", "产业链图谱库", "cognition", "杨辰、雅馨", "openks/kg/cognition/industry_chain", "定义产业网链主结构，承接事实要素并组织链路。", ("news_kg", "report_kg", "enterprise_kg", "technology_kg", "product_kg")),
    SeedModule("supply_chain", "供应链图谱库", "cognition", "待定", "openks/kg/cognition/supply_chain", "建模供应依赖、替代关系与脆弱点。", ("industry_chain",)),
    SeedModule("innovation_chain", "创新链图谱库", "cognition", "待定", "openks/kg/cognition/innovation_chain", "追踪技术创新、成果转化和协同主体。", ("industry_chain",)),
    SeedModule("capital_chain", "资金链图谱库", "cognition", "待定", "openks/kg/cognition/capital_chain", "建模投融资关系与资金流向。", ("industry_chain",)),
    SeedModule("technology_foresight", "技术前瞻", "decision", "林辉、徐梓毓", "openks/kg/decision/technology_foresight", "输出技术前瞻、路线分叉与长期趋势。", ("innovation_chain",)),
    SeedModule("hotspot", "热点分析", "decision", "待定", "openks/kg/decision/hotspot", "聚合热点、热度传播与行业焦点。", ("industry_chain", "supply_chain")),
    SeedModule("trend", "趋势分析", "decision", "待定", "openks/kg/decision/trend", "输出趋势判断、变化拐点和结构演进。", ("industry_chain", "innovation_chain", "capital_chain")),
    SeedModule("risk_alert", "风险预警", "decision", "待定", "openks/kg/decision/risk_alert", "输出供应、政策和波动风险预警。", ("supply_chain", "capital_chain")),
    SeedModule("recommendation", "推荐决策", "decision", "待定", "openks/kg/decision/recommendation", "面向智能体与应用层输出推荐与排序结果。", ("trend", "hotspot", "risk_alert")),
]


def camelize(module_name: str) -> str:
    return "".join(part.capitalize() for part in module_name.split("_"))


def ensure_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def ensure_module_toml(module_root: Path, spec) -> None:
    payload = textwrap.dedent(
        f"""
        name = "{spec.name}"
        title = "{spec.title}"
        stage = "{spec.stage}"
        owner = "{spec.owner}"
        status = "skeleton"
        summary = "{spec.summary}"
        dependencies = {list(spec.dependencies)}
        """
    ).strip() + "\n"
    ensure_text(module_root / "module.toml", payload)


def ensure_runtime_files(module_root: Path, spec) -> None:
    class_prefix = camelize(spec.name)
    base_import = "from openks.common.base.core import BaseBuilder, BaseReasoner, BaseSchema, BaseSolver\n\n"

    ensure_text(
        module_root / "__init__.py",
        textwrap.dedent(
            f"""
            from .schema.{spec.name}_schema import {class_prefix}Schema
            from .builder.{spec.name}_builder import {class_prefix}Builder
            from .reasoner.{spec.name}_reasoner import {class_prefix}Reasoner
            from .solver.{spec.name}_solver import {class_prefix}Solver

            __all__ = [
                "{class_prefix}Schema",
                "{class_prefix}Builder",
                "{class_prefix}Reasoner",
                "{class_prefix}Solver",
            ]
            """
        ).strip()
        + "\n",
    )

    ensure_text(module_root / "schema" / "__init__.py", f"from .{spec.name}_schema import {class_prefix}Schema\n")
    ensure_text(
        module_root / "schema" / f"{spec.name}_schema.py",
        base_import
        + textwrap.dedent(
            f"""
            class {class_prefix}Schema(BaseSchema):
                def describe(self):
                    return {{
                        "entities": [{{"name": "{class_prefix}", "desc": "{spec.title}"}}],
                        "relations": [],
                        "fields": [],
                    }}
            """
        ).lstrip(),
    )

    ensure_text(module_root / "builder" / "__init__.py", f"from .{spec.name}_builder import {class_prefix}Builder\n")
    ensure_text(
        module_root / "builder" / f"{spec.name}_builder.py",
        base_import
        + textwrap.dedent(
            f"""
            class {class_prefix}Builder(BaseBuilder):
                def build(self, records):
                    return list(records)
            """
        ).lstrip(),
    )

    ensure_text(module_root / "reasoner" / "__init__.py", f"from .{spec.name}_reasoner import {class_prefix}Reasoner\n")
    ensure_text(
        module_root / "reasoner" / f"{spec.name}_reasoner.py",
        base_import
        + textwrap.dedent(
            f"""
            class {class_prefix}Reasoner(BaseReasoner):
                def infer(self, facts):
                    return list(facts)
            """
        ).lstrip(),
    )

    ensure_text(module_root / "solver" / "__init__.py", f"from .{spec.name}_solver import {class_prefix}Solver\n")
    ensure_text(
        module_root / "solver" / f"{spec.name}_solver.py",
        base_import
        + textwrap.dedent(
            f"""
            class {class_prefix}Solver(BaseSolver):
                def solve(self, query):
                    return {{"query": query, "results": []}}
            """
        ).lstrip(),
    )

    ensure_text(
        module_root / "config" / f"{spec.name}.yaml",
        textwrap.dedent(
            f"""
            graph_id: {spec.name}
            graph_type: {spec.stage}
            schema: openks.kg.{spec.stage}.{spec.name}.schema.{spec.name}_schema.{class_prefix}Schema
            builder: openks.kg.{spec.stage}.{spec.name}.builder.{spec.name}_builder.{class_prefix}Builder
            reasoner: openks.kg.{spec.stage}.{spec.name}.reasoner.{spec.name}_reasoner.{class_prefix}Reasoner
            solver: openks.kg.{spec.stage}.{spec.name}.solver.{spec.name}_solver.{class_prefix}Solver
            """
        ).strip()
        + "\n",
    )

    ensure_text(
        module_root / "tests" / f"test_{spec.name}.py",
        textwrap.dedent(
            f"""
            from openks.kg.{spec.stage}.{spec.name} import (
                {class_prefix}Builder,
                {class_prefix}Reasoner,
                {class_prefix}Schema,
                {class_prefix}Solver,
            )


            def test_{spec.name}_scaffold_runtime_contract():
                schema = {class_prefix}Schema()
                builder = {class_prefix}Builder()
                reasoner = {class_prefix}Reasoner()
                solver = {class_prefix}Solver()

                assert schema.describe()["entities"]
                assert builder.build([{{"id": 1}}]) == [{{"id": 1}}]
                assert reasoner.infer([{{"id": 1}}]) == [{{"id": 1}}]
                assert solver.solve({{"keyword": "demo"}})["query"] == {{"keyword": "demo"}}
            """
        ).strip()
        + "\n",
    )


def ensure_module_readme(module_root: Path, spec) -> None:
    readme = module_root / "README.md"
    if readme.exists():
        return
    ensure_text(
        readme,
        textwrap.dedent(
            f"""
            # {spec.title}

            - 模块名：`{spec.name}`
            - 负责人：{spec.owner}
            - 阶段：`{spec.stage}`
            - 当前状态：`skeleton`
            - 说明：{spec.summary}
            """
        ).strip()
        + "\n",
    )


def main() -> None:
    for spec in SEED_MODULES:
        module_root = ROOT / spec.path
        ensure_module_toml(module_root, spec)
        ensure_module_readme(module_root, spec)
        ensure_runtime_files(module_root, spec)


if __name__ == "__main__":
    main()
