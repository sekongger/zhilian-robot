from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "modules" / "kag" / "kag" / "examples" / "fact_library"
DEFAULT_CONFIG_PATH = EXAMPLE_DIR / "kag_config.yaml"
DEFAULT_ENV_PATH = EXAMPLE_DIR / ".env"


DEFAULTS = {
    "OPENSPG_HOST_ADDR": "http://127.0.0.1:8887",
    "FACT_LIBRARY_NAMESPACE": "FactLibrary",
    "FACT_LIBRARY_PROJECT_ID": "",
    "FACT_LIBRARY_DATASET": "20260313_183538",
    "FACT_LIBRARY_PROJECT_VISIBILITY": "PRIVATE",
    "FACT_LIBRARY_PROJECT_TAG": "LOCAL",
    "FACT_LIBRARY_PROJECT_USER_NO": "openspg",
    "FACT_LIBRARY_CHECKPOINT_PATH": "./ckpt",
    "FACT_LIBRARY_BIZ_SCENE": "default",
    "FACT_LIBRARY_LANGUAGE": "zh",
    "FACT_LIBRARY_OPENIE_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "FACT_LIBRARY_OPENIE_API_KEY": "",
    "FACT_LIBRARY_OPENIE_MODEL": "qwen2.5-7b-instruct-1m",
    "FACT_LIBRARY_CHAT_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "FACT_LIBRARY_CHAT_API_KEY": "",
    "FACT_LIBRARY_CHAT_MODEL": "qwen2.5-72b-instruct",
    "FACT_LIBRARY_VECTOR_BASE_URL": "https://api.siliconflow.cn/v1",
    "FACT_LIBRARY_VECTOR_API_KEY": "",
    "FACT_LIBRARY_VECTOR_MODEL": "BAAI/bge-m3",
    "FACT_LIBRARY_VECTOR_DIMENSIONS": "1024",
    "FACT_LIBRARY_VECTOR_TYPE": "",
}


def parse_env_file(env_file: Optional[Path]) -> Dict[str, str]:
    if env_file is None or not env_file.exists():
        return {}
    values: Dict[str, str] = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        values[key] = value
    return values


def load_settings(
    env_file: Optional[Path] = None,
    overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    settings = dict(DEFAULTS)
    settings.update(parse_env_file(env_file))
    for key in DEFAULTS:
        if key in os.environ and os.environ[key] != "":
            settings[key] = os.environ[key]
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                settings[key] = value
    return settings


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _yaml_int_or_null(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "null"
    return str(int(text))


def build_vectorizer_config(settings: Dict[str, str]) -> Dict[str, object]:
    vector_api_key = (settings.get("FACT_LIBRARY_VECTOR_API_KEY") or "").strip()
    vector_type = (settings.get("FACT_LIBRARY_VECTOR_TYPE") or "").strip().lower()
    if not vector_type:
        vector_type = "mock" if not vector_api_key else "openai"

    vector_dimensions = int(settings["FACT_LIBRARY_VECTOR_DIMENSIONS"])
    vector_model = settings["FACT_LIBRARY_VECTOR_MODEL"]

    if vector_type == "mock":
        model_name = vector_model or "mock_vectorize_model"
        return {
            "type": "mock",
            "model": model_name,
            "name": model_name,
            "vector_dimensions": vector_dimensions,
            "enable_check": False,
        }

    return {
        "api_key": vector_api_key,
        "base_url": settings["FACT_LIBRARY_VECTOR_BASE_URL"],
        "model": vector_model,
        "type": vector_type,
        "vector_dimensions": vector_dimensions,
        "enable_check": False,
    }


def build_config_dict(settings: Dict[str, str]) -> Dict[str, object]:
    project_id = (settings.get("FACT_LIBRARY_PROJECT_ID") or "").strip()
    vectorizer_config = build_vectorizer_config(settings)
    return {
        "openie_llm": {
            "type": "maas",
            "base_url": settings["FACT_LIBRARY_OPENIE_BASE_URL"],
            "api_key": settings["FACT_LIBRARY_OPENIE_API_KEY"],
            "model": settings["FACT_LIBRARY_OPENIE_MODEL"],
            "enable_check": False,
        },
        "chat_llm": {
            "type": "maas",
            "base_url": settings["FACT_LIBRARY_CHAT_BASE_URL"],
            "api_key": settings["FACT_LIBRARY_CHAT_API_KEY"],
            "model": settings["FACT_LIBRARY_CHAT_MODEL"],
            "enable_check": False,
        },
        "vectorize_model": dict(vectorizer_config),
        "vectorizer": dict(vectorizer_config),
        "log": {
            "level": "INFO",
        },
        "project": {
            "biz_scene": settings["FACT_LIBRARY_BIZ_SCENE"],
            "host_addr": settings["OPENSPG_HOST_ADDR"],
            "id": int(project_id) if project_id else None,
            "language": settings["FACT_LIBRARY_LANGUAGE"],
            "namespace": settings["FACT_LIBRARY_NAMESPACE"],
            "checkpoint_path": settings["FACT_LIBRARY_CHECKPOINT_PATH"],
        },
    }


def build_config_yaml(settings: Dict[str, str]) -> str:
    namespace = settings["FACT_LIBRARY_NAMESPACE"]
    vectorizer_config = build_vectorizer_config(settings)
    vectorize_yaml_lines = [
        f"  type: {_yaml_string(str(vectorizer_config['type']))}",
        f"  model: {_yaml_string(str(vectorizer_config['model']))}",
        f"  vector_dimensions: {int(vectorizer_config['vector_dimensions'])}",
        "  enable_check: false",
    ]
    if "name" in vectorizer_config:
        vectorize_yaml_lines.insert(2, f"  name: {_yaml_string(str(vectorizer_config['name']))}")
    if "base_url" in vectorizer_config:
        vectorize_yaml_lines.insert(1, f"  base_url: {_yaml_string(str(vectorizer_config['base_url']))}")
    if "api_key" in vectorizer_config:
        vectorize_yaml_lines.insert(2 if "base_url" in vectorizer_config else 1, f"  api_key: {_yaml_string(str(vectorizer_config['api_key']))}")
    vectorize_yaml = "\n".join(vectorize_yaml_lines)
    return f"""# This file is generated by scripts/fact_library/render_fact_library_kag_config.py
#------------project configuration start----------------#
openie_llm: &openie_llm
  type: maas
  base_url: {_yaml_string(settings["FACT_LIBRARY_OPENIE_BASE_URL"])}
  api_key: {_yaml_string(settings["FACT_LIBRARY_OPENIE_API_KEY"])}
  model: {_yaml_string(settings["FACT_LIBRARY_OPENIE_MODEL"])}
  enable_check: false

chat_llm: &chat_llm
  type: maas
  base_url: {_yaml_string(settings["FACT_LIBRARY_CHAT_BASE_URL"])}
  api_key: {_yaml_string(settings["FACT_LIBRARY_CHAT_API_KEY"])}
  model: {_yaml_string(settings["FACT_LIBRARY_CHAT_MODEL"])}
  enable_check: false

vectorize_model: &vectorize_model
{vectorize_yaml}
vectorizer: *vectorize_model

log:
  level: INFO

project:
  biz_scene: {_yaml_string(settings["FACT_LIBRARY_BIZ_SCENE"])}
  host_addr: {_yaml_string(settings["OPENSPG_HOST_ADDR"])}
  id: {_yaml_int_or_null(settings["FACT_LIBRARY_PROJECT_ID"])}
  language: {_yaml_string(settings["FACT_LIBRARY_LANGUAGE"])}
  namespace: {_yaml_string(namespace)}
  checkpoint_path: {_yaml_string(settings["FACT_LIBRARY_CHECKPOINT_PATH"])}
#------------project configuration end----------------#

#------------kag-builder configuration start----------------#
entity_runner:
  chain:
    type: structured_builder_chain
    mapping:
      type: spg_mapping
    writer:
      type: kg_writer
  scanner:
    type: csv_scanner

relation_runner:
  chain:
    type: structured_builder_chain
    mapping:
      type: spo_mapping
      s_id_col: s_id
      s_type_col: s_type
      p_type_col: p
      o_id_col: o_id
      o_type_col: o_type
      sub_property_col: properties
    writer:
      type: kg_writer
  scanner:
    type: csv_scanner

text_runner:
  chain:
    type: unstructured_builder_chain
    extractor:
      type: schema_free_extractor
      llm: *openie_llm
      ner_prompt:
        type: default_ner
      std_prompt:
        type: default_std
      triple_prompt:
        type: default_triple
    reader:
      type: dict_reader
      content_col: text
      id_col: id
      name_col: name
    post_processor:
      type: kag_post_processor
    splitter:
      type: length_splitter
      split_length: 4000
      window_length: 200
    vectorizer:
      type: batch_vectorizer
      vectorize_model: *vectorize_model
    writer:
      type: kg_writer
  num_threads_per_chain: 2
  num_chains: 4
  scanner:
    type: csv_scanner
#------------kag-builder configuration end----------------#
"""


def write_config(settings: Dict[str, str], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_config_yaml(settings), encoding="utf-8")
    return output_path
