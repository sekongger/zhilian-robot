from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import time
from typing import Any


DEFAULT_NAIVE_TZ = timezone(timedelta(hours=8))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=DEFAULT_NAIVE_TZ)
    return value.astimezone(timezone.utc)


def parse_datetime_to_utc(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return _to_utc(value)

    if isinstance(value, time.struct_time):
        epoch_seconds = calendar.timegm(value)
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)

    raw = str(value).strip()
    if not raw:
        return None

    # RFC3339 with Z support.
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return _to_utc(parsed)
    except ValueError:
        pass

    # RFC2822 / RFC822 (common in RSS).
    try:
        parsed = parsedate_to_datetime(raw)
        return _to_utc(parsed)
    except (TypeError, ValueError):
        pass

    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in fmts:
        try:
            parsed = datetime.strptime(raw, fmt)
            return _to_utc(parsed)
        except ValueError:
            continue
    return None


def is_within_hours(target: datetime | None, hours: int) -> bool:
    if target is None:
        return True
    cutoff = utc_now() - timedelta(hours=max(hours, 0))
    return target >= cutoff
