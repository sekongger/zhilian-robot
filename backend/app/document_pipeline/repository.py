from datetime import datetime
from typing import Dict, List, Optional
from .utils import generate_doc_id, generate_microcontent_id, hash_content, split_microcontent


class DocumentRepository:
    def __init__(self, db):
        self.db = db

    def build_resource_doc(self, resource_type, source, title, content, url):
        content_hash = hash_content((title or "") + (content or ""))
        return {
            "resource_doc_id": generate_doc_id(),
            "resource_type": resource_type,
            "data_source": source,
            "title_raw": title,
            "raw_content": content,
            "url": url,
            "content_hash": content_hash,
            "crawl_time": datetime.utcnow(),
            "status": "pending",
        }

    def build_inc_document(
        self,
        resource_doc: Dict,
        summary: Optional[str] = None,
        resource_file_id: Optional[str] = None,
        extra_meta: Optional[Dict] = None,
    ) -> Dict:
        return {
            "doc_id": resource_doc["resource_doc_id"],
            "resource_doc_id": resource_doc["resource_doc_id"],
            "resource_file_id": resource_file_id,
            "title": resource_doc.get("title_raw"),
            "content": resource_doc.get("raw_content") or "",
            "summary": summary or "",
            "data_source": resource_doc.get("data_source"),
            "ds_id": resource_doc.get("ds_id"),
            "publish_time": resource_doc.get("publish_time"),
            "source_info": resource_doc.get("source_info"),
            "status": "active",
            "process_batch_id": resource_doc.get("process_batch_id"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "resource_type": resource_doc.get("resource_type"),
            "extra_meta": extra_meta or {},
        }

    def build_microcontent(self, doc_id: str, content: str, process_batch_id: Optional[str] = None) -> List[Dict]:
        blocks = split_microcontent(content)
        results = []
        for idx, block in enumerate(blocks):
            results.append({
                "microcontent_id": generate_microcontent_id(),
                "doc_id": doc_id,
                "block_type": "paragraph",
                "block": block,
                "source_position": {"index": idx},
                "status": "active",
                "process_batch_id": process_batch_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        return results
