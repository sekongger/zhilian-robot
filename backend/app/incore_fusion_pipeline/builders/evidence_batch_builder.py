"""Build document, chunk, and evidence edges."""

from __future__ import annotations

from typing import List, Tuple

from app.incore_fusion_pipeline.dto.canonical_dto import CanonicalEventDTO
from app.incore_fusion_pipeline.dto.graph_import_dto import GraphEdgeUpsertDTO, GraphNodeUpsertDTO
from app.incore_fusion_pipeline.dto.normalized_dto import NormalizedChunkDTO, NormalizedDocumentDTO


class EvidenceBatchBuilder:
    """Translate document and chunk inputs into graph nodes and evidence edges."""

    def build(
        self,
        documents: List[NormalizedDocumentDTO],
        chunks: List[NormalizedChunkDTO],
        events: List[CanonicalEventDTO],
    ) -> Tuple[List[GraphNodeUpsertDTO], List[GraphNodeUpsertDTO], List[GraphEdgeUpsertDTO]]:
        document_nodes = [
            GraphNodeUpsertDTO(
                type_name="Document",
                graph_id=f"Document:{doc.document_id}",
                name=doc.name,
                properties={
                    key: value
                    for key, value in {
                        "description": doc.description,
                        "docType": doc.doc_type,
                        "externalId": doc.document_id,
                        "url": doc.url,
                        "publishTime": doc.publish_time,
                        "semanticType": "Document",
                    }.items()
                    if value not in (None, "", [])
                },
            )
            for doc in documents
        ]

        chunk_nodes = [
            GraphNodeUpsertDTO(
                type_name="Chunk",
                graph_id=f"Chunk:{chunk.chunk_id}",
                name=f"Chunk {chunk.chunk_index}",
                properties={
                    key: value
                    for key, value in {
                        "content": chunk.content,
                        "chunkIndex": chunk.chunk_index,
                        "startOffset": chunk.start_offset,
                        "endOffset": chunk.end_offset,
                        "description": f"Chunk from {chunk.document_id}",
                    }.items()
                    if value not in (None, "", [])
                },
            )
            for chunk in chunks
        ]

        edges: List[GraphEdgeUpsertDTO] = []
        chunk_lookup = {chunk.chunk_id: f"Chunk:{chunk.chunk_id}" for chunk in chunks}
        doc_lookup = {doc.document_id: f"Document:{doc.document_id}" for doc in documents}

        for chunk in chunks:
            if chunk.document_id in doc_lookup:
                edges.append(
                    GraphEdgeUpsertDTO(
                        subject_graph_id=f"Chunk:{chunk.chunk_id}",
                        predicate="source",
                        object_graph_id=doc_lookup[chunk.document_id],
                    )
                )

        for event in events:
            for document_id in event.evidence.document_ids:
                doc_graph_id = doc_lookup.get(document_id)
                if doc_graph_id:
                    edges.append(
                        GraphEdgeUpsertDTO(
                            subject_graph_id=event.graph_id,
                            predicate="mentionedIn",
                            object_graph_id=doc_graph_id,
                        )
                    )
            for chunk_id in event.evidence.chunk_ids:
                chunk_graph_id = chunk_lookup.get(chunk_id)
                if chunk_graph_id:
                    edges.append(
                        GraphEdgeUpsertDTO(
                            subject_graph_id=event.graph_id,
                            predicate="evidenceChunk",
                            object_graph_id=chunk_graph_id,
                        )
                    )

        return document_nodes, chunk_nodes, self._dedupe_edges(edges)

    @staticmethod
    def _dedupe_edges(edges: List[GraphEdgeUpsertDTO]) -> List[GraphEdgeUpsertDTO]:
        deduped: List[GraphEdgeUpsertDTO] = []
        seen = set()
        for edge in edges:
            key = (edge.subject_graph_id, edge.predicate, edge.object_graph_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped
