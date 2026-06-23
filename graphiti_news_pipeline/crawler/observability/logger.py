from __future__ import annotations

import logging
import os
from pathlib import Path


def setup_logging() -> None:
    level_name = os.getenv("CRAWLER_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_dir_raw = os.getenv("CRAWLER_LOG_DIR", "").strip()
    if log_dir_raw:
        log_dir = Path(log_dir_raw)
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "crawler.log", encoding="utf-8"))
    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)
