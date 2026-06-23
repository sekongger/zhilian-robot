"""Normalization helpers used across resolvers and builders."""

from __future__ import annotations

import re


_COMPANY_SUFFIX_PATTERN = re.compile(
    r"(有限责任公司|股份有限公司|有限公司|集团有限公司|集团股份有限公司|集团|公司|厂)$"
)

_REGION_SUFFIXES = (
    "特别行政区",
    "维吾尔自治区",
    "回族自治区",
    "壮族自治区",
    "自治区",
    "省",
    "市",
    "地区",
    "盟",
    "自治州",
    "区",
    "县",
)

_DIRECT_MUNICIPALITIES = {"北京", "上海", "天津", "重庆"}


def normalize_text_key(value: str | None) -> str:
    """Return a compact comparison key."""

    text = str(value or "").strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("（", "(").replace("）", ")")
    return text or "unknown"


def normalize_company_core_name(value: str | None) -> str:
    """Return a weaker company alias key for fuzzy actor matching."""

    text = normalize_text_key(value)
    text = _COMPANY_SUFFIX_PATTERN.sub("", text)
    return text or normalize_text_key(value)


def normalize_region_name(value: str | None) -> str:
    """Normalize region names so province/city references can align."""

    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("内蒙古自治区", "内蒙古")
    text = text.replace("广西壮族自治区", "广西")
    text = text.replace("宁夏回族自治区", "宁夏")
    text = text.replace("新疆维吾尔自治区", "新疆")
    text = text.replace("西藏自治区", "西藏")
    text = text.replace("香港特别行政区", "香港")
    text = text.replace("澳门特别行政区", "澳门")
    for suffix in _REGION_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return normalize_text_key(text)


def infer_region_category(*, province: str | None = None, city: str | None = None, raw_name: str | None = None) -> str:
    """Infer the coarse region category used by Region.category."""

    if city:
        return "地市级行政区"
    normalized = normalize_region_name(raw_name or province)
    if normalized in _DIRECT_MUNICIPALITIES:
        return "省级行政区"
    return "省级行政区"


def build_region_graph_id(*, province: str | None = None, city: str | None = None, raw_name: str | None = None) -> str:
    """Build a stable graph id for region entities."""

    normalized_province = normalize_region_name(province or raw_name)
    normalized_city = normalize_region_name(city)
    if normalized_city and normalized_city != normalized_province:
        return f"Region:{normalized_province}/{normalized_city}"
    return f"Region:{normalized_province or normalize_region_name(raw_name)}"
