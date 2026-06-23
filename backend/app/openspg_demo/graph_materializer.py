"""将 workflow 导出的 JSONL 批次稳定写入 OpenSPG 图。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import httpx


COMPANY_PATTERN = re.compile(
    r"([\u4e00-\u9fa5A-Za-z0-9·]{2,24}(?:机器人|车企|科技|智能|集团|股份|公司|厂|研究院|电信))"
)
PRODUCT_PATTERN = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9 ._-]{1,24}(?:手机|机器人|机械臂|设备|平台|系统|鱼缸|产线)|[\u4e00-\u9fa5A-Za-z0-9·]{2,32}(?:手机|机器人|机械臂|设备|平台|系统|鱼缸|产线))"
)
PRODUCT_MODEL_PATTERN = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9 ._-]{1,24})\s*([\u4e00-\u9fa5]{0,8}(?:手机|机器人|机械臂|设备|平台|系统|鱼缸|产线))"
)
TECH_KEYWORDS = [
    "具身智能",
    "机器视觉",
    "伺服",
    "减速器",
    "控制器",
    "SLAM",
    "大模型",
    "工业机器人",
    "协作机器人",
    "人形机器人",
    "自动化产线",
    "路径规划",
]

GENERIC_COMPANY_NAMES = {
    "一家AI公司",
    "他的创业公司",
    "创业公司",
    "控股公司",
    "子公司",
    "全资子公司",
    "某公司",
    "某机器人公司",
}

COMPANY_NOISE_FRAGMENTS = (
    "应用",
    "维修中心",
    "焊接",
    "机械臂",
    "控制平台",
    "产线",
    "场景",
    "方案",
    "效率",
    "能力",
    "调度",
)

GENERIC_PRODUCT_PREFIXES = (
    "方案将把",
    "将把",
    "拓展",
    "面向",
    "升级",
    "联合",
    "合作",
)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _trim_text(value: Any, limit: int) -> str:
    text = _safe_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _type_name(namespace: str, local_name: str) -> str:
    if not namespace or "." in local_name:
        return local_name
    return f"{namespace}.{local_name}"


def _chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for idx in range(0, len(items), size):
        yield items[idx: idx + size]


def _split_text_segments(text: str) -> List[str]:
    raw_parts = re.split(
        r"[，。；：、\n\r\t]|(?:联合|联手|携手|合作|达成|推进|拓展|面向|与|和|及其|以及|并与|发布了|发布|表示|称|声明|推出)",
        text,
    )
    parts = []
    for item in raw_parts:
        token = _safe_text(item)
        if token:
            parts.append(token)
    return parts


def _normalize_company_name(text: str) -> str:
    value = _safe_text(text)
    value = re.sub(r"^(网传|有关|关于|其全资子公司|全资子公司|子公司|旗下|严正|消息|称|表示)+", "", value)
    value = re.sub(r"(无任何关联|该信息不实|相关信息不实)$", "", value)
    value = re.sub(r"^(的|对外展示了|两款|样品|手机产品|产品)", "", value)
    value = value.strip("，。；：、()（）[]【】 ")
    return _trim_text(value, 64)


def _is_generic_company_name(text: str) -> bool:
    value = _safe_text(text)
    if not value:
        return True
    if value in GENERIC_COMPANY_NAMES:
        return True
    if value in TECH_KEYWORDS or value in {"协作机器人"}:
        return True
    if value.startswith(("双方", "方案", "围绕", "面向")):
        return True
    if "能力" in value and "智能" in value:
        return True
    if value.endswith("机器人") and (len(value) > 8 or any(flag in value for flag in COMPANY_NOISE_FRAGMENTS)):
        return True
    if any(flag in value for flag in COMPANY_NOISE_FRAGMENTS) and not value.endswith(("科技", "智能", "集团", "股份", "公司", "厂", "研究院", "电信")):
        return True
    if value.startswith(("一家", "某", "该")) and value.endswith(("公司", "集团")):
        return True
    return False


def _is_generic_product_name(text: str, company_names: List[str]) -> bool:
    value = _safe_text(text)
    if not value:
        return True
    if value in company_names:
        return True
    if value.startswith(GENERIC_PRODUCT_PREFIXES):
        return True
    return False


def _normalize_product_name(text: str) -> str:
    value = _safe_text(text)
    value = re.sub(r"^(两款|样品|型号|网传|发布了|推出了|对外展示了)", "", value)
    value = re.sub(r"(无任何关联|该信息不实)$", "", value)
    value = value.strip("，。；：、()（）[]【】 ")
    return _trim_text(value, 80)


def _extract_companies(title: str, content: str) -> List[str]:
    values: List[str] = []
    segments = _split_text_segments(f"{title} {content}")
    for segment in segments:
        normalized_segment = _normalize_company_name(segment)
        if not normalized_segment:
            continue
        for match in COMPANY_PATTERN.findall(normalized_segment):
            name = _normalize_company_name(match)
            if len(name) < 2 or _is_generic_company_name(name) or name in values:
                continue
            values.append(name)
    return values[:6]


def _extract_products(title: str, content: str) -> List[str]:
    values: List[str] = []
    company_names = _extract_companies(title, content)
    segments = _split_text_segments(f"{title} {content}")
    for segment in segments:
        normalized_segment = _normalize_product_name(segment)
        if not normalized_segment:
            continue
        model_match = PRODUCT_MODEL_PATTERN.search(normalized_segment)
        if model_match:
            name = _normalize_product_name(f"{model_match.group(1)} {model_match.group(2)}")
            if len(name) >= 2 and not _is_generic_product_name(name, company_names) and name not in values:
                values.append(name)
        for match in PRODUCT_PATTERN.findall(normalized_segment):
            name = _normalize_product_name(match)
            if (
                len(name) < 2
                or name in {"机器人产业", "机器人产业链"}
                or _is_generic_product_name(name, company_names)
                or name in values
            ):
                continue
            values.append(name)
    return values[:6]


def _extract_techs(title: str, content: str) -> List[str]:
    text = f"{title} {content}".strip()
    result: List[str] = []
    for keyword in TECH_KEYWORDS:
        if keyword in text and keyword not in result:
            result.append(keyword)
    return result[:6]


async def _get_project_namespace(*, project_id: int, openspg_base_url: str) -> str:
    env_ns = _safe_text(os.getenv("OPENSPG_DEMO_NAMESPACE"))
    if env_ns:
        return env_ns

    async with httpx.AsyncClient(base_url=openspg_base_url.rstrip("/"), timeout=15.0) as client:
        try:
            response = await client.get("/public/v1/project", params={"projectId": project_id})
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return "zhilian"

    if isinstance(payload, list) and payload:
        row = payload[0] if isinstance(payload[0], dict) else {}
    elif isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list) and data:
            row = data[0] if isinstance(data[0], dict) else {}
        elif isinstance(data, dict):
            row = data
        else:
            row = payload
    else:
        row = {}
    namespace = _safe_text(row.get("namespace"))
    return namespace or "zhilian"


async def _post_json(openspg_base_url: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(base_url=openspg_base_url.rstrip("/"), timeout=60.0) as client:
        response = await client.post(path, json=payload)
        response.raise_for_status()
        result = response.json()
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(f"{path} failed: {result}")
    return result if isinstance(result, dict) else {"result": result}


async def _upsert_vertices(*, project_id: int, openspg_base_url: str, vertices: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await _post_json(
        openspg_base_url,
        "/public/v1/graph/upsertVertex",
        {"projectId": project_id, "vertices": vertices},
    )


async def _upsert_edges(*, project_id: int, openspg_base_url: str, edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    return await _post_json(
        openspg_base_url,
        "/public/v1/graph/upsertEdge",
        {"projectId": project_id, "upsertAdjacentVertices": False, "edges": edges},
    )


def _build_vertices_and_edges(records: List[Dict[str, Any]], namespace: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    document_type = _type_name(namespace, "Document")
    chunk_type = _type_name(namespace, "Chunk")
    company_type = _type_name(namespace, "Company")
    product_type = _type_name(namespace, "Product")
    technology_type = _type_name(namespace, "Technology")
    knowledge_point_type = _type_name(namespace, "KnowledgePoint")

    vertices: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    for rec in records:
        doc_id = _safe_text(rec.get("doc_id"))
        if not doc_id:
            continue
        title = _trim_text(rec.get("title") or "未命名资讯", 256)
        summary = _trim_text(rec.get("summary"), 1024)
        content = _trim_text(rec.get("content"), 8000)
        source_name = _trim_text(rec.get("source_name") or "unknown", 128)
        source_url = _trim_text(rec.get("source_url"), 1024)
        publish_time = _safe_text(rec.get("publish_time"))
        crawl_time = _safe_text(rec.get("crawl_time"))

        chunk_id = "CHK_" + hashlib.sha1(doc_id.encode("utf-8")).hexdigest()[:20]
        evidence = _trim_text(summary or content or title, 240)
        chunk_content = f"{title}\n{summary}\n{content}".strip()

        vertices.append(
            {
                "type": document_type,
                "id": doc_id,
                "properties": {
                    "name": title,
                    "title": title,
                    "description": evidence,
                    "source": source_name,
                    "url": source_url,
                    "publishTime": publish_time,
                    "crawlTime": crawl_time,
                    "sentiment": "中立",
                    "viewCount": 0,
                    "commentCount": 0,
                    "shareCount": 0,
                },
            }
        )
        vertices.append(
            {
                "type": chunk_type,
                "id": chunk_id,
                "properties": {
                    "name": title,
                    "content": chunk_content,
                    "description": _trim_text(f"source={source_name}; url={source_url}", 1024),
                },
            }
        )

        companies = _extract_companies(title, content)
        products = _extract_products(title, content)
        techs = _extract_techs(title, content)

        for company_name in companies:
            company_id = "COM_" + hashlib.sha1(company_name.encode("utf-8")).hexdigest()[:20]
            vertices.append(
                {
                    "type": company_type,
                    "id": company_id,
                    "properties": {
                        "name": company_name,
                        "description": "资讯抽取实体",
                    },
                }
            )
            edges.append(
                {
                    "srcType": document_type,
                    "srcId": doc_id,
                    "dstType": company_type,
                    "dstId": company_id,
                    "label": "mentionsCompany",
                    "properties": {"name": "mentionsCompany"},
                }
            )
            kp_id = "KP_" + hashlib.sha1(f"{doc_id}|mentionsCompany|{company_id}".encode("utf-8")).hexdigest()[:24]
            vertices.append(
                {
                    "type": knowledge_point_type,
                    "id": kp_id,
                    "properties": {
                        "name": _trim_text(title, 100),
                        "description": "资讯关系抽取",
                        "confidence": 0.6,
                        "evidenceText": evidence,
                        "extractTime": crawl_time or publish_time,
                        "subjectName": title,
                        "predicateName": "mentionsCompany",
                        "objectName": company_name,
                    },
                }
            )
            edges.extend(
                [
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": chunk_type,
                        "dstId": chunk_id,
                        "label": "fromChunk",
                        "properties": {"name": "fromChunk"},
                    },
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": company_type,
                        "dstId": company_id,
                        "label": "linkObjCompany",
                        "properties": {"name": "linkObjCompany"},
                    },
                ]
            )

        for product_name in products:
            product_id = "PROD_" + hashlib.sha1(product_name.encode("utf-8")).hexdigest()[:20]
            vertices.append(
                {
                    "type": product_type,
                    "id": product_id,
                    "properties": {
                        "name": product_name,
                        "description": "资讯抽取产品实体",
                        "applicationCase": evidence,
                    },
                }
            )
            edges.append(
                {
                    "srcType": document_type,
                    "srcId": doc_id,
                    "dstType": product_type,
                    "dstId": product_id,
                    "label": "mentionsProduct",
                    "properties": {"name": "mentionsProduct"},
                }
            )
            kp_id = "KP_" + hashlib.sha1(f"{doc_id}|mentionsProduct|{product_id}".encode("utf-8")).hexdigest()[:24]
            vertices.append(
                {
                    "type": knowledge_point_type,
                    "id": kp_id,
                    "properties": {
                        "name": _trim_text(title, 100),
                        "description": "资讯关系抽取",
                        "confidence": 0.6,
                        "evidenceText": evidence,
                        "extractTime": crawl_time or publish_time,
                        "subjectName": title,
                        "predicateName": "mentionsProduct",
                        "objectName": product_name,
                    },
                }
            )
            edges.extend(
                [
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": chunk_type,
                        "dstId": chunk_id,
                        "label": "fromChunk",
                        "properties": {"name": "fromChunk"},
                    },
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": product_type,
                        "dstId": product_id,
                        "label": "linkObjProduct",
                        "properties": {"name": "linkObjProduct"},
                    },
                ]
            )

        for tech_name in techs:
            tech_id = "TECH_" + hashlib.sha1(tech_name.encode("utf-8")).hexdigest()[:20]
            vertices.append(
                {
                    "type": technology_type,
                    "id": tech_id,
                    "properties": {
                        "name": tech_name,
                        "description": "资讯抽取技术实体",
                        "maturityLevel": "unknown",
                    },
                }
            )
            edges.append(
                {
                    "srcType": document_type,
                    "srcId": doc_id,
                    "dstType": technology_type,
                    "dstId": tech_id,
                    "label": "mentionsTech",
                    "properties": {"name": "mentionsTech"},
                }
            )

    vertex_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in vertices:
        key = (item["type"], item["id"])
        if key not in vertex_map:
            vertex_map[key] = item
            continue
        exists = vertex_map[key]["properties"]
        for k, v in item["properties"].items():
            if v and not exists.get(k):
                exists[k] = v

    edge_map: Dict[Tuple[str, str, str, str, str], Dict[str, Any]] = {}
    for item in edges:
        key = (item["srcType"], item["srcId"], item["label"], item["dstType"], item["dstId"])
        if key not in edge_map:
            edge_map[key] = item

    return list(vertex_map.values()), list(edge_map.values())


async def _materialize_bridge_batch_async(
    *,
    batch_file_path: str,
    project_id: int,
    openspg_base_url: str,
) -> Dict[str, Any]:
    batch_file = Path(batch_file_path)
    if not batch_file.exists():
        raise FileNotFoundError(f"batch file not found: {batch_file_path}")

    records: List[Dict[str, Any]] = []
    for line in batch_file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if isinstance(payload, dict):
            records.append(payload)

    namespace = await _get_project_namespace(project_id=project_id, openspg_base_url=openspg_base_url)
    vertices, edges = _build_vertices_and_edges(records, namespace)

    vertex_groups = 0
    edge_groups = 0
    for chunk in _chunked(vertices, 50):
        await _upsert_vertices(project_id=project_id, openspg_base_url=openspg_base_url, vertices=chunk)
        vertex_groups += 1
    for chunk in _chunked(edges, 100):
        await _upsert_edges(project_id=project_id, openspg_base_url=openspg_base_url, edges=chunk)
        edge_groups += 1

    return {
        "status": "success",
        "project_id": project_id,
        "namespace": namespace,
        "records": len(records),
        "vertices": len(vertices),
        "edges": len(edges),
        "vertex_groups": vertex_groups,
        "edge_groups": edge_groups,
        "batch_file_path": str(batch_file),
    }


def materialize_bridge_batch(
    *,
    batch_file_path: str,
    project_id: int,
    openspg_base_url: str | None = None,
) -> Dict[str, Any]:
    base_url = _safe_text(openspg_base_url or os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887")
    return asyncio.run(
        _materialize_bridge_batch_async(
            batch_file_path=batch_file_path,
            project_id=project_id,
            openspg_base_url=base_url,
        )
    )


async def async_materialize_bridge_batch(
    *,
    batch_file_path: str,
    project_id: int,
    openspg_base_url: str | None = None,
) -> Dict[str, Any]:
    base_url = _safe_text(openspg_base_url or os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887")
    return await _materialize_bridge_batch_async(
        batch_file_path=batch_file_path,
        project_id=project_id,
        openspg_base_url=base_url,
    )
