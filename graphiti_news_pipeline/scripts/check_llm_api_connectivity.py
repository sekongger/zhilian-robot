from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


def _required_env(name: str) -> str:
    value = str(os.getenv(name, "")).strip()
    if not value:
        raise RuntimeError(f"missing env: {name}")
    return value


def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text[:1000]}


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    api_key = _required_env("OPENAI_API_KEY")
    base = _required_env("OPENAI_API_BASE").rstrip("/")
    model = _required_env("OPENAI_MODEL")
    timeout_seconds = int(os.getenv("LLM_CONNECT_TIMEOUT_SECONDS", "30"))

    endpoint = f"{base}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 16,
        "messages": [
            {"role": "system", "content": "You are a connectivity checker."},
            {"role": "user", "content": "Reply with exactly: pong"},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    started = time.time()
    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )
        elapsed_ms = int((time.time() - started) * 1000)
        body = _safe_json(resp)

        if resp.ok:
            content = ""
            try:
                content = str(body.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            except Exception:
                content = ""
            print(
                json.dumps(
                    {
                        "ok": True,
                        "endpoint": endpoint,
                        "model": model,
                        "status_code": resp.status_code,
                        "elapsed_ms": elapsed_ms,
                        "reply_preview": content[:200],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        print(
            json.dumps(
                {
                    "ok": False,
                    "endpoint": endpoint,
                    "model": model,
                    "status_code": resp.status_code,
                    "elapsed_ms": elapsed_ms,
                    "error": body,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        print(
            json.dumps(
                {
                    "ok": False,
                    "endpoint": endpoint,
                    "model": model,
                    "elapsed_ms": elapsed_ms,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
