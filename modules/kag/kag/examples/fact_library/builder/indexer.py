import argparse
import copy
import csv
import os
from pathlib import Path

from kag.builder.runner import BuilderChainRunner
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path


ENTITY_TYPE_MAPPING = {
    "company": "Company",
    "institution": "Institution",
    "investor": "Investor",
    "person": "Person",
    "product": "Product",
    "project": "Project",
    "patent": "Patent",
    "article": "Article",
    "achievement": "Achievement",
    "standard_local": "StandardLocal",
    "standard_industry": "StandardIndustry",
    "standard_nation": "StandardNation",
    "ranking_list": "RankingList",
}


TEXT_FILE_ORDER = [
    "company.csv",
    "institution.csv",
    "investor.csv",
    "person.csv",
    "product.csv",
    "project.csv",
    "patent.csv",
    "article.csv",
    "achievement.csv",
    "standard_local.csv",
    "standard_industry.csv",
    "standard_nation.csv",
    "ranking_list.csv",
]

NAME_SOURCE_MAPPING = {
    "company": "name",
    "institution": "name",
    "investor": "name",
    "person": "name",
    "product": "name",
    "project": "name",
    "patent": "title_cn",
    "article": "title",
    "achievement": "name",
    "standard_local": "standard_name",
    "standard_industry": "standard_name",
    "standard_nation": "standard_name",
    "ranking_list": "name",
}

SKIP_SOURCE_COLUMNS = {"update_time"}
STRUCTURED_NUM_CHAINS = int(os.getenv("FACT_LIBRARY_STRUCTURED_NUM_CHAINS", "16"))
STRUCTURED_NUM_THREADS_PER_CHAIN = int(
    os.getenv("FACT_LIBRARY_STRUCTURED_NUM_THREADS_PER_CHAIN", "1")
)


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "backend" / "data" / "fact_library").exists():
            return parent
    raise RuntimeError("repo root not found")


def _processed_dataset_dir(dataset_name: str) -> Path:
    return _find_repo_root() / "backend" / "data" / "fact_library" / "processed" / dataset_name


def _snake_to_camel(value: str) -> str:
    if "_" not in value:
        return value
    head, *tail = value.split("_")
    return head + "".join(item[:1].upper() + item[1:] for item in tail if item)


def _read_csv_header(file_path: Path) -> list[str]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        return next(reader)


def _build_property_mapping(file_name: str, file_path: Path) -> dict[str, str]:
    header = _read_csv_header(file_path)
    mapping: dict[str, str] = {"id": "id"}
    name_source = NAME_SOURCE_MAPPING.get(file_name)
    if name_source and name_source in header:
        mapping["name"] = name_source
    for column in header:
        if column in {"id", "name"} or column in SKIP_SOURCE_COLUMNS:
            continue
        mapping[_snake_to_camel(column)] = column
    return mapping


def import_entities(dataset_name: str) -> None:
    entity_runner_config = KAG_CONFIG.all_config["entity_runner"]
    entity_dir = _processed_dataset_dir(dataset_name) / "entities"
    for file_name, spg_type_name in ENTITY_TYPE_MAPPING.items():
        file_path = entity_dir / f"{file_name}.csv"
        if not file_path.exists():
            continue
        runner_config = copy.deepcopy(entity_runner_config)
        runner_config["chain"]["mapping"]["spg_type_name"] = spg_type_name
        runner_config["chain"]["mapping"]["property_mapping"] = _build_property_mapping(
            file_name,
            file_path,
        )
        runner_config["num_chains"] = STRUCTURED_NUM_CHAINS
        runner_config["num_threads_per_chain"] = STRUCTURED_NUM_THREADS_PER_CHAIN
        runner = BuilderChainRunner.from_config(runner_config)
        runner.invoke(str(file_path))


def import_relations(dataset_name: str) -> None:
    relation_runner_config = KAG_CONFIG.all_config["relation_runner"]
    relation_dir = _processed_dataset_dir(dataset_name) / "relations"
    if not relation_dir.exists():
        return
    for file_path in sorted(relation_dir.glob("*.csv")):
        runner_config = copy.deepcopy(relation_runner_config)
        runner_config["num_chains"] = STRUCTURED_NUM_CHAINS
        runner_config["num_threads_per_chain"] = STRUCTURED_NUM_THREADS_PER_CHAIN
        runner = BuilderChainRunner.from_config(runner_config)
        runner.invoke(str(file_path))


def import_texts(dataset_name: str) -> None:
    text_runner_config = KAG_CONFIG.all_config["text_runner"]
    text_dir = _processed_dataset_dir(dataset_name) / "texts"
    for file_name in TEXT_FILE_ORDER:
        file_path = text_dir / file_name
        if not file_path.exists():
            continue
        runner = BuilderChainRunner.from_config(copy.deepcopy(text_runner_config))
        runner.invoke(str(file_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import fact library data into KAG/OpenSPG.")
    parser.add_argument(
        "--dataset",
        default="20260313_183538",
        help="Dataset name under backend/data/fact_library/processed",
    )
    parser.add_argument(
        "--with-text",
        action="store_true",
        help="Run schema-free extraction on texts/*.csv after structured import",
    )
    args = parser.parse_args()

    import_modules_from_path(".")
    import_entities(args.dataset)
    import_relations(args.dataset)
    if args.with_text:
        import_texts(args.dataset)


if __name__ == "__main__":
    main()
