"""Map source envelopes into normalized DTOs."""

from __future__ import annotations

from typing import List, Tuple

from app.incore_fusion_pipeline.dto.normalized_dto import (
    ConceptCandidateDTO,
    MatchReferenceDTO,
    NormalizedChunkDTO,
    NormalizedConceptSeedDTO,
    NormalizedDocumentDTO,
    NormalizedEntityDTO,
    NormalizedEventDTO,
    NormalizedRelationDTO,
)
from app.incore_fusion_pipeline.dto.source_dto import SourceRecordDTO


class SourceMapper:
    """Translate source-level envelopes into normalized DTOs."""

    def map_record(self, record: SourceRecordDTO):
        payload = record.payload or {}
        source_ref = record.to_source_ref()
        record_type = record.record_type

        if record_type == "entity":
            aliases = self._list_value(payload.get("aliases"))
            external_keys = {}
            code = payload.get("code")
            if code:
                external_keys["code"] = str(code)
            if payload.get("credit_code"):
                external_keys["credit_code"] = str(payload["credit_code"])

            properties = dict(payload.get("properties") or {})
            for field in ("status", "website", "description", "business_scope", "province", "city"):
                if payload.get(field) is not None:
                    key = "businessScope" if field == "business_scope" else field
                    properties[key] = payload[field]
            if payload.get("name_en") is not None:
                properties["nameEn"] = payload["name_en"]
            if payload.get("job_title") is not None:
                properties["jobTitle"] = payload["job_title"]

            concept_candidates = self._concept_candidates_from_payload(payload)
            return NormalizedEntityDTO(
                canonical_type=payload.get("entity_type", "Unknown"),
                source_refs=[source_ref],
                primary_name=payload.get("name", ""),
                aliases=aliases,
                external_keys=external_keys,
                properties=properties,
                concept_candidates=concept_candidates,
            )

        if record_type == "relation":
            properties = dict(payload.get("properties") or {})
            if payload.get("confidence") is not None:
                properties["confidence"] = payload["confidence"]
            if payload.get("effective_time") is not None:
                properties["effectiveTime"] = payload["effective_time"]
            return NormalizedRelationDTO(
                subject_ref=MatchReferenceDTO(
                    type=payload.get("subject_type", "Unknown"),
                    match_key=str(payload.get("subject_key", "")),
                ),
                predicate=payload.get("predicate", ""),
                object_ref=MatchReferenceDTO(
                    type=payload.get("object_type", "Unknown"),
                    match_key=str(payload.get("object_key", "")),
                ),
                properties=properties,
                source_refs=[source_ref],
            )

        if record_type == "document":
            source = {
                "name": payload.get("source_name"),
                "source_type": payload.get("source_type"),
                "authority_level": payload.get("authority_level"),
            }
            return NormalizedDocumentDTO(
                document_id=record.record_id,
                doc_type=payload.get("doc_type", "unknown"),
                name=payload.get("title", record.record_id),
                description=payload.get("summary"),
                content=payload.get("content"),
                publish_time=payload.get("publish_time"),
                url=payload.get("url"),
                source=source,
                source_refs=[source_ref],
            )

        if record_type == "chunk":
            document_id = str(payload.get("doc_id") or "")
            chunk_index = int(payload.get("chunk_index") or 0)
            return NormalizedChunkDTO(
                chunk_id=record.record_id if record.record_id else f"{document_id}#{chunk_index}",
                document_id=document_id,
                chunk_index=chunk_index,
                start_offset=payload.get("start_offset"),
                end_offset=payload.get("end_offset"),
                content=payload.get("content", ""),
                source_refs=[source_ref],
            )

        if record_type == "event":
            properties = dict(payload.get("properties") or {})
            for source_key, target_key in (
                ("event_time", "eventTime"),
                ("publish_time", "publishTime"),
                ("confidence", "confidence"),
                ("financing_amount", "financingAmount"),
                ("financing_round", "financingRound"),
                ("location", "location"),
            ):
                if payload.get(source_key) is not None:
                    properties[target_key] = payload[source_key]
            if payload.get("trigger_terms") is not None:
                properties["triggerTerms"] = self._list_value(payload.get("trigger_terms"), allow_scalar=True)
            if payload.get("policy_no") is not None:
                properties["policyNo"] = payload["policy_no"]
            if payload.get("policy_level") is not None:
                properties["policyLevel"] = payload["policy_level"]
            if payload.get("policy_type") is not None:
                properties["policyType"] = payload["policy_type"]
            if payload.get("cooperation_mode") is not None:
                properties["cooperationMode"] = payload["cooperation_mode"]
            if payload.get("contract_amount") is not None:
                properties["contractAmount"] = payload["contract_amount"]
            if payload.get("financing_purpose") is not None:
                properties["financingPurpose"] = payload["financing_purpose"]
            if payload.get("impact_category") is not None:
                properties["impactCategory"] = payload["impact_category"]

            return NormalizedEventDTO(
                event_type=payload.get("event_type", "Event"),
                name=payload.get("name") or record.record_id,
                summary=payload.get("summary"),
                subject_ref=self._optional_match_ref("Company", payload.get("subject_name")),
                object_ref=self._optional_match_ref("IndustryActor", payload.get("object_name")),
                location_ref=self._optional_match_ref("Region", payload.get("location")),
                category_ref=self._optional_match_ref("EventCategory", payload.get("category")),
                source_document_ids=self._list_value(payload.get("source_doc_id"), allow_scalar=True),
                source_chunk_ids=self._list_value(payload.get("source_chunk_ids"), allow_scalar=True),
                properties=properties,
                concept_candidates=self._concept_candidates_from_payload(payload),
                source_refs=[source_ref],
            )

        if record_type == "concept_seed":
            return NormalizedConceptSeedDTO(
                concept_type=payload.get("concept_type", ""),
                name=payload.get("name", ""),
                parent_name=payload.get("parent_name"),
                aliases=self._list_value(payload.get("aliases")),
                description=payload.get("description"),
                properties=dict(payload.get("properties") or {}),
                source_refs=[source_ref],
            )

        raise ValueError(f"Unsupported record type: {record_type}")

    def map_records(self, records: List[SourceRecordDTO]) -> Tuple[
        List[NormalizedEntityDTO],
        List[NormalizedRelationDTO],
        List[NormalizedDocumentDTO],
        List[NormalizedChunkDTO],
        List[NormalizedEventDTO],
        List[NormalizedConceptSeedDTO],
    ]:
        entities: List[NormalizedEntityDTO] = []
        relations: List[NormalizedRelationDTO] = []
        documents: List[NormalizedDocumentDTO] = []
        chunks: List[NormalizedChunkDTO] = []
        events: List[NormalizedEventDTO] = []
        concept_seeds: List[NormalizedConceptSeedDTO] = []

        for record in records:
            mapped = self.map_record(record)
            if isinstance(mapped, NormalizedEntityDTO):
                entities.append(mapped)
            elif isinstance(mapped, NormalizedRelationDTO):
                relations.append(mapped)
            elif isinstance(mapped, NormalizedDocumentDTO):
                documents.append(mapped)
            elif isinstance(mapped, NormalizedChunkDTO):
                chunks.append(mapped)
            elif isinstance(mapped, NormalizedEventDTO):
                events.append(mapped)
            elif isinstance(mapped, NormalizedConceptSeedDTO):
                concept_seeds.append(mapped)

        return entities, relations, documents, chunks, events, concept_seeds

    @staticmethod
    def _list_value(value, allow_scalar: bool = False) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        if allow_scalar and value not in (None, ""):
            return [str(value)]
        return []

    @staticmethod
    def _optional_match_ref(type_name: str, value: str | None):
        if value in (None, ""):
            return None
        return MatchReferenceDTO(type=type_name, match_key=str(value))

    @staticmethod
    def _concept_candidates_from_payload(payload) -> List[ConceptCandidateDTO]:
        concept_candidates: List[ConceptCandidateDTO] = []
        for item in payload.get("concept_candidates", []) or []:
            if not item:
                continue
            concept_candidates.append(
                ConceptCandidateDTO(
                    concept_type=str(item.get("concept_type", "")),
                    concept_name=str(item.get("concept_name", "")),
                    score=float(item.get("score", 0.0)),
                )
            )
        return concept_candidates
