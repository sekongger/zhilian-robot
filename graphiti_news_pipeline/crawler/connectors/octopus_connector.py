from __future__ import annotations

from dataclasses import dataclass
import logging
import json
import os
from typing import Any, Callable

import requests

from crawler.connectors.base import BaseConnector
from crawler.domain.enums import ArticleStatus
from crawler.domain.models import ArticleRecord, SourceConfig
from crawler.services.canonical_url_service import canonicalize_url
from crawler.services.octopus_clean_service import OctopusLLMCleaner
from crawler.utils.hash_utils import build_article_id
from crawler.utils.text_utils import normalize_text
from crawler.utils.time_utils import is_within_hours, parse_datetime_to_utc, utc_now

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OctopusFetchResult:
    records: list[ArticleRecord]
    exported_task_ids: list[str]


class OctopusConnector(BaseConnector):
    """
    Fetches unexported data from Bazhuayu OpenAPI and maps records to crawler articles.
    This connector pre-cleans content and directly emits DEDUP_PASSED records
    so downstream can continue with compress -> ingest.
    """

    def __init__(self) -> None:
        self.cleaner = OctopusLLMCleaner()
        self.base_url = os.getenv("OCTOPUS_API_BASE", "https://openapi.bazhuayu.com").strip().rstrip("/")
        self.timeout_seconds = int(os.getenv("CRAWLER_OCTOPUS_HTTP_TIMEOUT_SECONDS", "30"))

    def fetch(self, source: SourceConfig, since_hours: int, max_items: int) -> list[ArticleRecord]:
        result = self.fetch_with_meta(source, since_hours=since_hours, max_items=max_items)
        return result.records

    def fetch_with_meta(
        self,
        source: SourceConfig,
        since_hours: int,
        max_items: int,
        should_keep: Callable[[ArticleRecord], bool] | None = None,
    ) -> OctopusFetchResult:
        options = source.options or {}
        username = str(options.get("username", "")).strip() or os.getenv("OCTOPUS_USERNAME", "").strip()
        password = str(options.get("password", "")).strip() or os.getenv("OCTOPUS_PASSWORD", "").strip()
        if not username or not password:
            logger.warning("Octopus source=%s missing credentials.", source.source_id)
            return OctopusFetchResult(records=[], exported_task_ids=[])

        token = self._get_token(username=username, password=password)
        if not token:
            return OctopusFetchResult(records=[], exported_task_ids=[])

        task_ids = self._resolve_task_ids(token=token, options=options)
        if not task_ids:
            logger.info("Octopus source=%s no matched task ids.", source.source_id)
            return OctopusFetchResult(records=[], exported_task_ids=[])

        records: list[ArticleRecord] = []
        exported_task_ids: list[str] = []
        for task_id in task_ids:
            task_records = self._fetch_task_records_all(
                token=token,
                source=source,
                task_id=task_id,
                since_hours=since_hours,
                max_items=max_items,
                should_keep=should_keep,
            )
            records.extend(task_records)
            # data/all is account history and does not require markexported mutation.
            # Keep the return shape stable but do not emit task ids for mark-exported.

        return OctopusFetchResult(records=records, exported_task_ids=exported_task_ids)

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": token,
        }

    def _get_token(self, *, username: str, password: str) -> str:
        url = f"{self.base_url}/token"
        payload = {
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        try:
            response = requests.post(url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            resp = response.json()
            access_token = str(((resp.get("data") or {}).get("access_token") or "")).strip()
            if not access_token:
                logger.warning("Octopus token response missing access_token.")
                return ""
            return f"Bearer {access_token}"
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("Octopus get token failed: %s", exc)
            return ""

    def _resolve_task_ids(self, *, token: str, options: dict[str, Any]) -> list[str]:
        explicit_task_ids = options.get("task_ids", [])
        env_task_ids = os.getenv("OCTOPUS_TASK_IDS", "").strip()
        if not explicit_task_ids and env_task_ids:
            explicit_task_ids = [item.strip() for item in env_task_ids.split(",") if item.strip()]
        if isinstance(explicit_task_ids, str):
            explicit_task_ids = [explicit_task_ids]
        if isinstance(explicit_task_ids, list):
            parsed = [str(item).strip() for item in explicit_task_ids if str(item).strip()]
            if parsed:
                return parsed

        group_name = (
            str(options.get("task_group_name", "")).strip()
            or os.getenv("OCTOPUS_TASK_GROUP_NAME", "").strip()
        )
        if not group_name:
            return []

        try:
            group_url = f"{self.base_url}/taskGroup"
            group_resp = requests.get(group_url, headers=self._headers(token), timeout=self.timeout_seconds)
            group_resp.raise_for_status()
            groups = (group_resp.json() or {}).get("data", []) or []
            group_id = None
            for group in groups:
                if str(group.get("taskGroupName", "")).strip() == group_name:
                    group_id = group.get("taskGroupId")
                    break
            if not group_id:
                return []

            task_url = f"{self.base_url}/task/search?taskGroupId={group_id}"
            task_resp = requests.get(task_url, headers=self._headers(token), timeout=self.timeout_seconds)
            task_resp.raise_for_status()
            tasks = (task_resp.json() or {}).get("data", []) or []
            task_name_allowlist = options.get("task_names", [])
            env_task_names = os.getenv("OCTOPUS_TASK_NAMES", "").strip()
            if not task_name_allowlist and env_task_names:
                task_name_allowlist = [item.strip() for item in env_task_names.split(",") if item.strip()]
            if isinstance(task_name_allowlist, str):
                task_name_allowlist = [task_name_allowlist]
            allowlist = {str(item).strip() for item in task_name_allowlist if str(item).strip()}

            result: list[str] = []
            for task in tasks:
                task_id = str(task.get("taskId", "")).strip()
                task_name = str(task.get("taskName", "")).strip()
                if not task_id:
                    continue
                if allowlist and task_name not in allowlist:
                    continue
                result.append(task_id)
            return result
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("Octopus resolve task ids failed: %s", exc)
            return []

    def _fetch_task_records_all(
        self,
        *,
        token: str,
        source: SourceConfig,
        task_id: str,
        since_hours: int,
        max_items: int,
        should_keep: Callable[[ArticleRecord], bool] | None = None,
    ) -> list[ArticleRecord]:
        records = self._fetch_task_records_by_endpoint(
            endpoint="/data/all",
            token=token,
            source=source,
            task_id=task_id,
            since_hours=since_hours,
            max_items=max_items,
            should_keep=should_keep,
        )
        if records:
            return records

        # Some octopus tasks expose backlog only from /data/notexported.
        # Fallback here avoids false "empty fetch" when /data/all returns no rows.
        logger.info(
            "Octopus data/all returned no records, fallback to data/notexported task=%s",
            task_id,
        )
        return self._fetch_task_records_by_endpoint(
            endpoint="/data/notexported",
            token=token,
            source=source,
            task_id=task_id,
            since_hours=since_hours,
            max_items=max_items,
            should_keep=should_keep,
        )

    def _fetch_task_records_by_endpoint(
        self,
        *,
        endpoint: str,
        token: str,
        source: SourceConfig,
        task_id: str,
        since_hours: int,
        max_items: int,
        should_keep: Callable[[ArticleRecord], bool] | None = None,
    ) -> list[ArticleRecord]:
        url = f"{self.base_url}{endpoint}"
        page_size = 100
        seed_params_candidates = [
            {"taskId": task_id, "size": page_size, "offset": 1},
            {"taskId": task_id, "size": page_size, "offset": 0},
            {"taskId": task_id, "size": page_size, "pageNo": 1},
            {"taskId": task_id, "size": page_size, "page": 1},
            {"taskId": task_id, "size": page_size},
        ]
        data_block: dict[str, Any] = {}
        params: dict[str, Any] | None = None
        last_error: Exception | None = None

        for candidate in seed_params_candidates:
            try:
                response = requests.get(
                    url,
                    headers=self._headers(token),
                    params=candidate,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json() or {}
                data_raw = payload.get("data", {}) or {}
                if not isinstance(data_raw, dict):
                    data_raw = {}
                rows = data_raw.get("data", []) or []
                total = self._safe_int(data_raw.get("total"), default=0)
                if rows or total > 0:
                    params = dict(candidate)
                    data_block = data_raw
                    break
            except (requests.RequestException, ValueError, TypeError) as exc:
                last_error = exc

        if params is None:
            if last_error is not None:
                logger.warning("Octopus fetch task data failed task=%s err=%s", task_id, last_error)
            return []

        records: list[ArticleRecord] = []
        seen_page_tokens: set[str] = set()
        max_pages = 1000
        scanned_pages = 0
        while scanned_pages < max_pages and len(records) < max_items:
            page_data = data_block.get("data", []) or []
            if not isinstance(page_data, list):
                page_data = []
            try:
                for item in page_data:
                    if not isinstance(item, dict):
                        continue
                    mapped = self._map_item(
                        source=source,
                        task_id=task_id,
                        item=item,
                        since_hours=since_hours,
                    )
                    if mapped is not None and (should_keep is None or should_keep(mapped)):
                        records.append(mapped)
                        if len(records) >= max_items:
                            break
            except Exception as exc:  # noqa: BLE001
                logger.warning("Octopus map task page failed task=%s err=%s", task_id, exc)
                break

            if len(records) >= max_items:
                break

            next_params = self._build_next_page_params(
                current_params=params,
                data_block=data_block,
                page_size=page_size,
            )
            if next_params is None:
                break
            page_token = json.dumps(next_params, sort_keys=True, ensure_ascii=False)
            if page_token in seen_page_tokens:
                break
            seen_page_tokens.add(page_token)
            params = next_params
            scanned_pages += 1

            try:
                response = requests.get(
                    url,
                    headers=self._headers(token),
                    params=params,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json() or {}
                data_raw = payload.get("data", {}) or {}
                if not isinstance(data_raw, dict):
                    data_raw = {}
                data_block = data_raw
            except (requests.RequestException, ValueError, TypeError) as exc:
                logger.warning("Octopus fetch task page failed task=%s err=%s", task_id, exc)
                break

        return records

    @staticmethod
    def _safe_int(value: Any, *, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_next_page_params(
        self,
        *,
        current_params: dict[str, Any],
        data_block: dict[str, Any],
        page_size: int,
    ) -> dict[str, Any] | None:
        next_params = dict(current_params)

        if "offset" in current_params:
            current_offset = current_params.get("offset")
            next_offset = data_block.get("offset")
            if next_offset is None or str(next_offset) == str(current_offset):
                return None
            next_params["offset"] = next_offset
            return next_params

        if "pageNo" in current_params:
            current_page = self._safe_int(current_params.get("pageNo"), default=1)
            total_page = self._safe_int(data_block.get("totalPage"), default=0)
            if total_page > 0 and current_page >= total_page:
                return None
            next_params["pageNo"] = current_page + 1
            return next_params

        if "page" in current_params:
            current_page = self._safe_int(current_params.get("page"), default=1)
            total_page = self._safe_int(data_block.get("totalPage"), default=0)
            if total_page <= 0:
                total_page = self._safe_int(data_block.get("pages"), default=0)
            if total_page > 0 and current_page >= total_page:
                return None
            next_params["page"] = current_page + 1
            return next_params

        rows = data_block.get("data", []) or []
        if isinstance(rows, list) and len(rows) >= page_size:
            next_params["pageNo"] = 2
            return next_params
        return None

    def mark_exported_tasks(self, source: SourceConfig, task_ids: list[str]) -> dict[str, int]:
        options = source.options or {}
        username = str(options.get("username", "")).strip() or os.getenv("OCTOPUS_USERNAME", "").strip()
        password = str(options.get("password", "")).strip() or os.getenv("OCTOPUS_PASSWORD", "").strip()
        if not username or not password:
            logger.warning("Octopus source=%s missing credentials when mark exported.", source.source_id)
            return {"total": 0, "marked": 0, "failed": 0}

        token = self._get_token(username=username, password=password)
        if not token:
            return {"total": len(task_ids), "marked": 0, "failed": len(task_ids)}

        marked = 0
        failed = 0
        deduped = [str(task_id).strip() for task_id in task_ids if str(task_id).strip()]
        deduped = list(dict.fromkeys(deduped))
        for task_id in deduped:
            if self._mark_exported(token=token, task_id=task_id):
                marked += 1
            else:
                failed += 1
        return {"total": len(deduped), "marked": marked, "failed": failed}

    def _mark_exported(self, *, token: str, task_id: str) -> bool:
        url = f"{self.base_url}/data/markexported"
        payload = {"taskId": task_id}
        try:
            response = requests.post(
                url,
                headers=self._headers(token),
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return True
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.warning("Octopus mark exported failed task=%s err=%s", task_id, exc)
            return False

    def _map_item(
        self,
        *,
        source: SourceConfig,
        task_id: str,
        item: dict[str, Any],
        since_hours: int,
    ) -> ArticleRecord | None:
        title = normalize_text(item.get("title", ""))
        if not title:
            return None

        raw_url = normalize_text(item.get("url", ""))
        canonical_url = canonicalize_url(raw_url)
        if not canonical_url:
            logger.warning("Octopus item skipped because original article url is missing: task=%s title=%s", task_id, title)
            return None

        publish_time = parse_datetime_to_utc(item.get("publish_time"))
        if not is_within_hours(publish_time, since_hours):
            return None

        raw_content = normalize_text(item.get("content", "")) or normalize_text(item.get("abstract", ""))
        if not raw_content:
            raw_content = title

        content_clean, used_llm = self.cleaner.clean(title=title, raw_text=raw_content)
        if not content_clean:
            return None

        publish_key = publish_time.isoformat() if publish_time else ""
        article_id = build_article_id(source.source_id, canonical_url, title, publish_key)
        tags = [str(t).strip() for t in (source.tags or []) if str(t).strip()]
        if "octopus" not in tags:
            tags.append("octopus")

        return ArticleRecord(
            article_id=article_id,
            source_id=source.source_id,
            source_name=source.name,
            source_url=source.url,
            title=title,
            content_raw=raw_content,
            publish_time_utc=publish_time,
            canonical_url=canonical_url,
            crawled_at_utc=utc_now(),
            status=ArticleStatus.DEDUP_PASSED,
            content_clean=content_clean,
            relevance_score=1.0,
            matched_keywords=tags,
            compress_error=None if used_llm else "octopus_clean_fallback_rule",
        )
