#!/usr/bin/env python3
import json
import pickle
import sqlite3
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parent
    db_path = base / "ckpt" / "SchemaConstraintExtractor" / "cache.db"
    out_path = base / "data" / "new1_company_entities.json"

    if not db_path.exists():
        raise FileNotFoundError(f"checkpoint not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("select value from Cache").fetchall()
    conn.close()

    entities = []
    dedup = set()
    for (value,) in rows:
        subgraphs = pickle.loads(value)
        for graph in subgraphs:
            for node in graph.nodes:
                if node.label != "Company":
                    continue
                key = (node.label, node.name)
                if key in dedup:
                    continue
                dedup.add(key)
                entities.append({"category": node.label, "name": node.name})

    out_path.write_text(
        json.dumps(entities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"exported {len(entities)} company entities to {out_path}")


if __name__ == "__main__":
    main()
