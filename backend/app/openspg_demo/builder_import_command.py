"""Builder 真导入命令与环境变量组装。"""

from __future__ import annotations

import base64
import gzip
import os
import textwrap
from pathlib import Path
from typing import Dict


_MAX_ENV_B64_LEN = 400_000


def build_real_import_command() -> str:
    """返回在 OpenSPG 计算引擎容器内执行的真实导入命令。"""
    return textwrap.dedent(
        """
        # OPENSPG_DEMO_REAL_IMPORT
        python3 - <<'PY'
        import base64
        import gzip
        import hashlib
        import json
        import os
        import re
        import sys
        import urllib.request

        def _is_exists_conflict(result):
            if not isinstance(result, dict):
                return False
            if result.get("success") is not False:
                return False
            message = str(result.get("errMessage") or result.get("message") or result)
            return "already exists" in message.lower()

        def _post_json(base_url, path, payload, timeout=30, ignore_exists=False):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                base_url.rstrip("/") + path,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
            except Exception:
                raise RuntimeError("invalid response for %s: %s" % (path, body[:500]))
            if isinstance(result, dict) and result.get("success") is False:
                if ignore_exists and _is_exists_conflict(result):
                    return {"success": True, "ignored": "already_exists", "raw": result}
                raise RuntimeError("request failed for %s: %s" % (path, result))
            if isinstance(result, str):
                raise RuntimeError("request failed for %s: %s" % (path, result[:500]))
            return result

        def _get_json(base_url, path, timeout=15):
            req = urllib.request.Request(
                base_url.rstrip("/") + path,
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
            except Exception:
                return {}
            return result if isinstance(result, (dict, list)) else {}

        def _resolve_project_namespace(base_url, project_id):
            env_ns = _safe_text(os.getenv("OPENSPG_DEMO_NAMESPACE"))
            if env_ns:
                return env_ns

            try:
                payload = _get_json(base_url, "/public/v1/project?projectId=%d" % project_id)
                if isinstance(payload, list) and payload:
                    first = payload[0] if isinstance(payload[0], dict) else {}
                elif isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, list) and data:
                        first = data[0] if isinstance(data[0], dict) else {}
                    elif isinstance(data, dict):
                        first = data
                    else:
                        first = payload
                else:
                    first = {}
                namespace = _safe_text(first.get("namespace"))
                if namespace:
                    return namespace
            except Exception:
                pass

            return "zhldemo"

        def _chunked(seq, size):
            for i in range(0, len(seq), size):
                yield seq[i : i + size]

        def _safe_text(val):
            if val is None:
                return ""
            return str(val).strip()

        def _trim_text(val, limit):
            text = _safe_text(val)
            if len(text) <= limit:
                return text
            return text[: limit - 1] + "…"

        def _type_name(namespace, local_name):
            if not namespace:
                return local_name
            if "." in local_name:
                return local_name
            return namespace + "." + local_name

        COMPANY_PATTERN = re.compile(
            r"([\\u4e00-\\u9fa5A-Za-z0-9·]{2,24}(?:机器人|车企|科技|智能|集团|股份|公司|厂|研究院))"
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

        def _extract_companies(title, content):
            text = (title + " " + content).strip()
            names = []
            for match in COMPANY_PATTERN.findall(text):
                name = match.strip("，。；：、()（）[]【】 ")
                if len(name) < 2:
                    continue
                if name not in names:
                    names.append(name)
            return names[:6]

        def _extract_techs(title, content):
            text = (title + " " + content).strip()
            result = []
            for keyword in TECH_KEYWORDS:
                if keyword in text and keyword not in result:
                    result.append(keyword)
            return result[:6]

        base_url = (os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887").strip()
        project_id = int(os.getenv("OPENSPG_DEMO_PROJECT_ID") or "1")
        namespace = _resolve_project_namespace(base_url, project_id)
        payload_b64 = os.getenv("OPENSPG_DEMO_BATCH_GZIP_B64") or ""
        if not payload_b64:
            raise RuntimeError("OPENSPG_DEMO_BATCH_GZIP_B64 is empty")

        raw = gzip.decompress(base64.b64decode(payload_b64)).decode("utf-8")
        records = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

        if not records:
            print(json.dumps({"status": "ok", "records": 0, "reason": "empty batch"}))
            sys.exit(0)

        document_type = _type_name(namespace, "Document")
        chunk_type = _type_name(namespace, "Chunk")
        company_type = _type_name(namespace, "Company")
        technology_type = _type_name(namespace, "Technology")
        knowledge_point_type = _type_name(namespace, "KnowledgePoint")

        vertices = []
        edges = []
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

            chunk_content = (title + "\\n" + summary + "\\n" + content).strip()
            chunk_desc = ("source=" + source_name + "; url=" + source_url).strip("; ")
            chunk_id = "CHK_" + hashlib.sha1(doc_id.encode("utf-8")).hexdigest()[:20]
            evidence = _trim_text((summary or content or title), 240)

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
                        "description": _trim_text(chunk_desc, 1024),
                    },
                }
            )

            companies = _extract_companies(title, content)
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

                kp_id = "KP_" + hashlib.sha1(
                    (doc_id + "|mentionsCompany|" + company_id).encode("utf-8")
                ).hexdigest()[:24]
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
                edges.append(
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": chunk_type,
                        "dstId": chunk_id,
                        "label": "fromChunk",
                        "properties": {"name": "fromChunk"},
                    }
                )
                edges.append(
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": company_type,
                        "dstId": company_id,
                        "label": "linkObjCompany",
                        "properties": {"name": "linkObjCompany"},
                    }
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
                            "hotScore": 0.0,
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

                kp_id = "KP_" + hashlib.sha1(
                    (doc_id + "|mentionsTech|" + tech_id).encode("utf-8")
                ).hexdigest()[:24]
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
                            "predicateName": "mentionsTech",
                            "objectName": tech_name,
                        },
                    }
                )
                edges.append(
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": chunk_type,
                        "dstId": chunk_id,
                        "label": "fromChunk",
                        "properties": {"name": "fromChunk"},
                    }
                )
                edges.append(
                    {
                        "srcType": knowledge_point_type,
                        "srcId": kp_id,
                        "dstType": technology_type,
                        "dstId": tech_id,
                        "label": "linkObjTech",
                        "properties": {"name": "linkObjTech"},
                    }
                )

        vertex_map = {}
        for item in vertices:
            key = (item["type"], item["id"])
            if key not in vertex_map:
                vertex_map[key] = item
                continue
            exists = vertex_map[key]["properties"]
            for k, v in item["properties"].items():
                if v and not exists.get(k):
                    exists[k] = v
        vertices = list(vertex_map.values())

        edge_map = {}
        for item in edges:
            key = (item["srcType"], item["srcId"], item["label"], item["dstType"], item["dstId"])
            if key not in edge_map:
                edge_map[key] = item
        edges = list(edge_map.values())

        # 清理历史脏数据：
        # 旧版本可能把同一 id 写成错误标签；Entity.id 全局唯一会阻塞本次正确标签写入。
        entity_ids = sorted({_safe_text(item.get("id")) for item in vertices if _safe_text(item.get("id"))})
        for ids_chunk in _chunked(entity_ids, 200):
            delete_vertices = [
                {"type": "Entity", "id": entity_id, "properties": {}}
                for entity_id in ids_chunk
            ]
            _post_json(
                base_url,
                "/public/v1/graph/deleteVertex",
                {"projectId": project_id, "vertices": delete_vertices},
            )

        vertex_groups = {}
        for item in vertices:
            vertex_groups.setdefault(item["type"], []).append(item)
        for vertex_type, grouped in vertex_groups.items():
            for chunk in _chunked(grouped, 50):
                _post_json(
                    base_url,
                    "/public/v1/graph/upsertVertex",
                    {"projectId": project_id, "vertices": chunk},
                    ignore_exists=True,
                )

        edge_groups = {}
        for item in edges:
            key = (item["srcType"], item["label"], item["dstType"])
            edge_groups.setdefault(key, []).append(item)
        for edge_type, grouped in edge_groups.items():
            for chunk in _chunked(grouped, 100):
                _post_json(
                    base_url,
                    "/public/v1/graph/upsertEdge",
                    {"projectId": project_id, "upsertAdjacentVertices": False, "edges": chunk},
                )

        print(
            json.dumps(
                {
                    "status": "ok",
                    "records": len(records),
                    "vertices": len(vertices),
                    "edges": len(edges),
                    "project_id": project_id,
                    "namespace": namespace,
                    "vertex_groups": len(vertex_groups),
                    "edge_groups": len(edge_groups),
                    "cleanup_entity_ids": len(entity_ids),
                },
                ensure_ascii=False,
            )
        )
        PY
        """
    ).strip()


def build_builder_envs_for_run(run_result: Dict, *, project_id: int) -> Dict[str, str]:
    """将桥接批次打包为 Builder 环境变量。"""
    batch_file_path = str(run_result.get("batch_file_path") or "").strip()
    if not batch_file_path:
        raise ValueError("batch_file_path is empty")

    batch_file = Path(batch_file_path)
    if not batch_file.exists():
        raise FileNotFoundError(f"batch file not found: {batch_file_path}")

    raw = batch_file.read_text(encoding="utf-8")
    encoded = base64.b64encode(gzip.compress(raw.encode("utf-8"))).decode("ascii")
    if len(encoded) > _MAX_ENV_B64_LEN:
        raise ValueError(
            f"batch payload too large for env var, len={len(encoded)}, max={_MAX_ENV_B64_LEN}"
        )

    openspg_base_url = (os.getenv("OPENSPG_BASE_URL") or "http://127.0.0.1:8887").strip()
    return {
        "OPENSPG_DEMO_BATCH_FILE": batch_file_path,
        "OPENSPG_DEMO_BATCH_FILE_NAME": str(run_result.get("batch_file_name") or batch_file.name),
        "OPENSPG_DEMO_BATCH_DOWNLOAD_URL": str(run_result.get("batch_download_url") or ""),
        "OPENSPG_DEMO_BATCH_GZIP_B64": encoded,
        "OPENSPG_DEMO_PROJECT_ID": str(project_id),
        "OPENSPG_BASE_URL": openspg_base_url,
    }
