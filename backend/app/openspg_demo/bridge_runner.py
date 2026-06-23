"""OpenSPG 演示桥接运行器：增量导出 JSONL 批次并维护本地状态。"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .bridge import normalize_news_record


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_time(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _record_event_time(record: Dict[str, Any]) -> Optional[datetime]:
    return _parse_time(record.get("publish_time")) or _parse_time(record.get("crawl_time"))


@dataclass
class BridgeRunner:
    data_dir: Optional[str] = None

    def __post_init__(self) -> None:
        root = self.data_dir or os.getenv("OPENSPG_DEMO_DATA_DIR")
        if not root:
            # zhilian-robot/backend/app/openspg_demo -> zhilian-robot/backend
            root = str(Path(__file__).resolve().parents[2] / "data" / "openspg_demo")
        self.base_dir = Path(root)
        self.batches_dir = self.base_dir / "batches"
        self.state_file = self.base_dir / "bridge_state.json"
        self.batches_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _default_state(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "cursor": {"last_seen_time": None},
            "last_run": None,
            "recent_runs": [],
        }

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return self._default_state()
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return self._default_state()
        if not isinstance(data, dict):
            return self._default_state()
        state = self._default_state()
        state.update(data)
        state.setdefault("cursor", {"last_seen_time": None})
        state.setdefault("recent_runs", [])
        return state

    def _save_state(self, state: Dict[str, Any]) -> None:
        tmp_file = self.state_file.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        tmp_file.replace(self.state_file)

    def get_status(self) -> Dict[str, Any]:
        state = self._load_state()
        state["data_dir"] = str(self.base_dir)
        state["batches_dir"] = str(self.batches_dir)
        return state

    def _select_incremental_records(
        self,
        normalized_rows: List[Dict[str, Any]],
        *,
        state: Dict[str, Any],
        force_full: bool,
        limit: int,
    ) -> List[Dict[str, Any]]:
        last_seen = _parse_time((state.get("cursor") or {}).get("last_seen_time"))
        candidates = normalized_rows
        if last_seen and not force_full:
            candidates = [
                row
                for row in normalized_rows
                if (_record_event_time(row) or _utc_now()) > last_seen
            ]

        candidates.sort(
            key=lambda row: _record_event_time(row) or _utc_now(),
            reverse=False,
        )
        if limit > 0:
            candidates = candidates[-limit:]
        return candidates

    def run_export(
        self,
        rows: Iterable[Dict[str, Any]],
        *,
        limit: int = 200,
        force_full: bool = False,
    ) -> Dict[str, Any]:
        state = self._load_state()
        normalized_rows = [normalize_news_record(row) for row in rows]
        selected = self._select_incremental_records(
            normalized_rows,
            state=state,
            force_full=force_full,
            limit=limit,
        )

        run_at = _utc_now()
        run_id = run_at.strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
        batch_file = self.batches_dir / f"{run_id}.jsonl"

        with batch_file.open("w", encoding="utf-8") as f:
            for row in selected:
                f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                f.write("\n")

        latest_seen_time = None
        if selected:
            latest_seen_dt = max((_record_event_time(row) or run_at) for row in selected)
            latest_seen_time = _to_iso(latest_seen_dt)
            state["cursor"] = {"last_seen_time": latest_seen_time}
        else:
            state.setdefault("cursor", {"last_seen_time": None})
            latest_seen_time = state["cursor"].get("last_seen_time")

        run_result = {
            "run_id": run_id,
            "status": "success",
            "run_time": _to_iso(run_at),
            "force_full": force_full,
            "input_count": len(normalized_rows),
            "export_count": len(selected),
            "cursor_after": {"last_seen_time": latest_seen_time},
            "batch_file_path": str(batch_file),
            "batch_file_name": batch_file.name,
            "batch_relative_path": f"batches/{batch_file.name}",
        }

        state["last_run"] = run_result
        recent_runs = [run_result, *(state.get("recent_runs") or [])]
        state["recent_runs"] = recent_runs[:20]
        self._save_state(state)
        return run_result

