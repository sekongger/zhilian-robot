"""Streaming reader for Wikidata JSON/JSONL records."""

from __future__ import annotations

import bz2
import gzip
import io
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional
from urllib.parse import urlparse
import urllib.request

from app.wiki_industry_pipeline.dto import WikiDumpRecordDTO


def iter_wikidata_records(
    path: str | Path,
    *,
    source: str = "wikidata",
    limit: Optional[int] = None,
    skip_records: int = 0,
    resume_cursor: int | None = None,
    cursor_callback: Callable[[int, int], None] | None = None,
    cursor_interval: int = 10000,
) -> Iterator[WikiDumpRecordDTO]:
    count = 0
    yielded = 0
    use_seekable_remote = resume_cursor is not None or cursor_callback is not None
    with _open_text(path, resume_cursor=resume_cursor, seekable_remote=use_seekable_remote) as handle:
        while True:
            line = handle.readline()
            if not line:
                break
            text = _clean_json_line(line)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            entity_id = str(payload.get("id") or "").strip()
            if not entity_id:
                continue
            count += 1
            if cursor_callback is not None and cursor_interval > 0 and count % cursor_interval == 0:
                cursor_callback(count, handle.tell())
            if count <= skip_records:
                continue
            yield WikiDumpRecordDTO(source=source, entity_id=entity_id, raw=payload)
            yielded += 1
            if limit is not None and yielded >= limit:
                break


def _open_text(path: str | Path, *, resume_cursor: int | None = None, seekable_remote: bool = False):
    source_path = str(path)
    if _is_url(source_path):
        return _open_remote_text(source_path, resume_cursor=resume_cursor, seekable=seekable_remote)

    resolved = Path(path)
    if resolved.suffix == ".bz2":
        handle = bz2.open(resolved, "rt", encoding="utf-8")
    elif resolved.suffix == ".gz":
        handle = gzip.open(resolved, "rt", encoding="utf-8")
    else:
        handle = resolved.open("r", encoding="utf-8")
    if resume_cursor is not None:
        handle.seek(resume_cursor)
    return handle


@contextmanager
def _open_remote_text(
    url: str,
    *,
    timeout: int = 60,
    resume_cursor: int | None = None,
    seekable: bool = False,
):
    if not seekable:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            compression = _compression_suffix(url)
            if compression == ".bz2":
                with bz2.BZ2File(response, "rb") as decompressed:
                    with io.TextIOWrapper(decompressed, encoding="utf-8") as handle:
                        yield handle
            elif compression == ".gz":
                with gzip.GzipFile(fileobj=response, mode="rb") as decompressed:
                    with io.TextIOWrapper(decompressed, encoding="utf-8") as handle:
                        yield handle
            else:
                with io.TextIOWrapper(response, encoding="utf-8") as handle:
                    yield handle
        return

    with HTTPRangeReader(url, timeout=timeout) as response:
        compression = _compression_suffix(url)
        if compression == ".bz2":
            with bz2.BZ2File(response, "rb") as decompressed:
                with io.TextIOWrapper(decompressed, encoding="utf-8") as handle:
                    if resume_cursor is not None:
                        handle.seek(resume_cursor)
                    yield handle
        elif compression == ".gz":
            with gzip.GzipFile(fileobj=response, mode="rb") as decompressed:
                with io.TextIOWrapper(decompressed, encoding="utf-8") as handle:
                    if resume_cursor is not None:
                        handle.seek(resume_cursor)
                    yield handle
        else:
            with io.TextIOWrapper(response, encoding="utf-8") as handle:
                if resume_cursor is not None:
                    handle.seek(resume_cursor)
                yield handle


class HTTPRangeReader(io.RawIOBase):
    """Minimal seekable HTTP reader backed by range requests."""

    def __init__(self, url: str, *, timeout: int = 60, block_size: int = 4 * 1024 * 1024):
        self.url = url
        self.timeout = timeout
        self.block_size = block_size
        self.position = 0
        self.buffer = b""
        self.buffer_start = 0
        self._closed = False

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.position = max(0, offset)
        elif whence == io.SEEK_CUR:
            self.position = max(0, self.position + offset)
        elif whence == io.SEEK_END:
            raise io.UnsupportedOperation("SEEK_END is not supported for HTTP range reads.")
        else:
            raise ValueError(f"Unsupported whence: {whence}")
        return self.position

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            return b""
        if size == 0:
            return b""
        if size < 0:
            chunks = []
            while True:
                chunk = self.read(self.block_size)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

        if not self._buffer_contains(self.position, size):
            self._fill_buffer(max(size, self.block_size))

        offset = self.position - self.buffer_start
        data = self.buffer[offset : offset + size]
        self.position += len(data)
        return data

    def readinto(self, b) -> int:
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n

    def close(self) -> None:
        self._closed = True
        super().close()

    def _buffer_contains(self, start: int, size: int) -> bool:
        if not self.buffer:
            return False
        if start < self.buffer_start:
            return False
        return start + size <= self.buffer_start + len(self.buffer)

    def _fill_buffer(self, desired_size: int) -> None:
        range_start = self.position
        range_end = range_start + desired_size - 1
        request = urllib.request.Request(
            self.url,
            headers={"Range": f"bytes={range_start}-{range_end}"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            self.buffer = response.read()
        self.buffer_start = range_start


def _is_url(path: str) -> bool:
    parsed = urlparse(path)
    return parsed.scheme in {"http", "https"}


def _compression_suffix(path_or_url: str) -> str:
    parsed = urlparse(path_or_url)
    path = parsed.path or path_or_url
    if path.endswith(".bz2"):
        return ".bz2"
    if path.endswith(".gz"):
        return ".gz"
    return ""


def _clean_json_line(line: str) -> str:
    text = line.strip()
    if text in {"", "[", "]"}:
        return ""
    if text.endswith(","):
        text = text[:-1].strip()
    return text
