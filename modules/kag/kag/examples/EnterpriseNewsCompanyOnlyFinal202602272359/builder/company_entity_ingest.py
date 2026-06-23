import hashlib
import json
import os
import re

from kag.builder.component.writer.kg_writer import KGWriter
from kag.builder.model.sub_graph import SubGraph
from kag.common.registry import import_modules_from_path


def _extract_companies(text: str) -> list[dict]:
    pattern = re.compile(r"[\u4e00-\u9fa5A-Za-z0-9·\\-]+(?:公司|集团)")
    names = {m.group(0).strip() for m in pattern.finditer(text)}
    if "英飞凌科技股份公司" in text:
        names.add("英飞凌科技股份公司")

    rows = []
    for name in sorted(names):
        rows.append(
            {
                "id": "company_" + hashlib.md5(name.encode("utf-8")).hexdigest()[:12],
                "name": name,
                "properties": {},
            }
        )
    return rows


def ingest(file_path: str):
    with open(file_path, "r", encoding="utf-8") as rf:
        text = rf.read()

    companies = _extract_companies(text)
    graph = SubGraph([], [])
    for item in companies:
        graph.add_node(
            id=item["id"],
            name=item["name"],
            label="Company",
            properties=item["properties"],
        )

    writer = KGWriter()
    writer.invoke(graph, write_ckpt=False)

    return companies


if __name__ == "__main__":
    import_modules_from_path(".")
    base_dir = os.path.dirname(__file__)
    input_file = os.path.join(base_dir, "data", "new1.md")
    output_file = os.path.join(base_dir, "data", "new1_company_entities.json")

    entities = ingest(input_file)
    payload = {
        "source_file": input_file,
        "entity_type": "Company",
        "count": len(entities),
        "entities": entities,
    }
    with open(output_file, "w", encoding="utf-8") as wf:
        json.dump(payload, wf, ensure_ascii=False, indent=2)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
