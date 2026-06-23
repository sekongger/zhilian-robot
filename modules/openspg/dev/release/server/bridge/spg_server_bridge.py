import json
import os
import threading
import time
from typing import Any, Dict, List

from kag.bridge.spg_server_bridge import SPGServerBridge as _SPGServerBridge

_MASKED = "******"
_PROMPT_TRACE_LOCK = threading.Lock()
_PROMPT_TRACE_PREFIX = "kag_prompt_trace_task_"
_PROMPT_TRACE_SUFFIX = ".jsonl"


def _default_api_key():
    return os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")


def _patch_api_key(node):
    fallback = _default_api_key()
    if isinstance(node, dict):
        if fallback and ("api_key" in node) and (
            not node.get("api_key") or node.get("api_key") == _MASKED
        ):
            node["api_key"] = fallback
        for value in node.values():
            _patch_api_key(value)
    elif isinstance(node, list):
        for item in node:
            _patch_api_key(item)
    return node


def _patch_vectorize_model(cfg):
    if not isinstance(cfg, dict):
        return
    vec_cfg = cfg.get("vectorize_model")
    if not isinstance(vec_cfg, dict):
        vec_cfg = {}
        cfg["vectorize_model"] = vec_cfg
    fallback_model = (
        os.getenv("OPENAI_EMBEDDING_MODEL")
        or os.getenv("VECTORIZE_MODEL")
        or "BAAI/bge-m3"
    )
    fallback_base_url = os.getenv("OPENAI_API_BASE") or "https://api.siliconflow.cn/v1"
    fallback_timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "120"))
    fallback_api_key = _default_api_key()
    provider = str(vec_cfg.get("provider", "")).lower()
    if not vec_cfg.get("type"):
        vec_cfg["type"] = "ollama" if provider == "ollama" else "openai"
    if not vec_cfg.get("model"):
        vec_cfg["model"] = fallback_model
    if not vec_cfg.get("base_url"):
        vec_cfg["base_url"] = fallback_base_url
    if not vec_cfg.get("timeout"):
        vec_cfg["timeout"] = fallback_timeout
    if fallback_api_key and not vec_cfg.get("api_key"):
        vec_cfg["api_key"] = fallback_api_key
    if not vec_cfg.get("name"):
        vec_cfg["name"] = (
            vec_cfg.get("model") or vec_cfg.get("modelId") or "vectorize_model"
        )


def _current_task_id() -> str:
    try:
        from kag.interface.common.llm_client import CURRENT_TASK_ID

        value = CURRENT_TASK_ID.get()
        return str(value or "default-task[0]")
    except Exception:
        return "default-task[0]"


def _trace_path(task_id: str) -> str:
    safe_task = str(task_id or "default-task[0]").replace("/", "_")
    return os.path.join(
        "/tmp", f"{_PROMPT_TRACE_PREFIX}{safe_task}{_PROMPT_TRACE_SUFFIX}"
    )


def _normalize_prompt(prompt: Any, messages: Any) -> str:
    if messages is not None:
        try:
            return json.dumps(messages, ensure_ascii=False)
        except Exception:
            return str(messages)
    if isinstance(prompt, str):
        return prompt
    try:
        return json.dumps(prompt, ensure_ascii=False)
    except Exception:
        return str(prompt)


def _record_prompt(model: str, api_base: str, prompt_name: str, prompt: Any, messages: Any):
    task_id = _current_task_id()
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "task_id": task_id,
        "model": str(model or "").strip(),
        "api_base": str(api_base or "").strip(),
        "prompt_name": str(prompt_name or "").strip(),
        "prompt": _normalize_prompt(prompt, messages),
    }
    path = _trace_path(task_id)
    try:
        with _PROMPT_TRACE_LOCK:
            with open(path, "a", encoding="utf-8") as writer:
                writer.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # prompt trace is best effort; extraction should not fail because of tracing
        return


def _load_prompt_trace(task_id: str) -> List[Dict[str, Any]]:
    path = _trace_path(task_id)
    if not os.path.exists(path):
        return []
    results: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as reader:
            for line in reader:
                text = str(line or "").strip()
                if not text:
                    continue
                try:
                    item = json.loads(text)
                except Exception:
                    continue
                if isinstance(item, dict):
                    results.append(item)
    except Exception:
        return []
    return results


def _remove_prompt_trace(task_id: str):
    path = _trace_path(task_id)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        return


def _patch_openai_like_client(cls):
    marker = f"_openspg_prompt_trace_patch_{cls.__name__}"
    if getattr(cls, marker, False):
        return

    original_call = cls.__call__
    original_acall = cls.acall

    def _wrapped_call(self, prompt: str = "", image_url: str = None, **kwargs):
        _record_prompt(
            model=getattr(self, "model", ""),
            api_base=getattr(self, "base_url", ""),
            prompt_name=kwargs.get("tag_name", ""),
            prompt=prompt,
            messages=kwargs.get("messages"),
        )
        return original_call(self, prompt=prompt, image_url=image_url, **kwargs)

    async def _wrapped_acall(self, prompt: str = "", image_url: str = None, **kwargs):
        _record_prompt(
            model=getattr(self, "model", ""),
            api_base=getattr(self, "base_url", ""),
            prompt_name=kwargs.get("tag_name", ""),
            prompt=prompt,
            messages=kwargs.get("messages"),
        )
        return await original_acall(self, prompt=prompt, image_url=image_url, **kwargs)

    cls.__call__ = _wrapped_call
    cls.acall = _wrapped_acall
    setattr(cls, marker, True)


def _install_prompt_trace_patch():
    try:
        from kag.common.llm.openai_client import AzureOpenAIClient, OpenAIClient
    except Exception:
        return
    _patch_openai_like_client(OpenAIClient)
    _patch_openai_like_client(AzureOpenAIClient)


class SPGServerBridge(_SPGServerBridge):
    def __init__(self):
        super().__init__()
        _install_prompt_trace_patch()

    def run_component(self, component_name, component_config, input_data):
        cfg = (
            json.loads(component_config)
            if isinstance(component_config, str)
            else component_config
        )
        cfg = _patch_api_key(cfg)
        if component_name == "VectorizerABC":
            _patch_vectorize_model(cfg)
        return super().run_component(component_name, cfg, input_data)

    def get_llm_token_info(self, task_id):
        data = super().get_llm_token_info(task_id)
        data = data if isinstance(data, dict) else {}
        prompts = _load_prompt_trace(str(task_id))
        if prompts:
            data["prompts"] = prompts
            last = prompts[-1]
            if isinstance(last, dict):
                data["model"] = last.get("model")
                data["api_base"] = last.get("api_base")
        _remove_prompt_trace(str(task_id))
        return data
