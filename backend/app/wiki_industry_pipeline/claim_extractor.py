"""Claim extraction from normalized Wikidata candidates."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.wiki_industry_pipeline.dto import WikiClaimDTO, WikiEntityCandidateDTO


class WikiClaimExtractor:
    def extract(self, candidate: WikiEntityCandidateDTO) -> List[WikiClaimDTO]:
        claims: List[WikiClaimDTO] = []
        for property_id, property_claims in candidate.claims.items():
            for raw_claim in property_claims or []:
                claim = self._extract_one(candidate, property_id, raw_claim)
                if claim is not None:
                    claims.append(claim)
        return claims

    def _extract_one(
        self,
        candidate: WikiEntityCandidateDTO,
        property_id: str,
        raw_claim: Dict[str, Any],
    ) -> Optional[WikiClaimDTO]:
        datavalue = ((raw_claim.get("mainsnak") or {}).get("datavalue") or {})
        if "value" not in datavalue:
            return None
        datatype = datavalue.get("type")
        value = datavalue.get("value")
        value_id = None
        value_literal = None
        value_datatype = str(datatype) if datatype else None

        if datatype == "wikibase-entityid" and isinstance(value, dict):
            value_id = str(value.get("id") or "")
            if not value_id and value.get("numeric-id") is not None:
                value_id = f"Q{value.get('numeric-id')}"
            value_id = value_id or None
        elif datatype == "time" and isinstance(value, dict):
            value_literal = value.get("time")
        elif datatype == "quantity" and isinstance(value, dict):
            value_literal = value.get("amount")
        else:
            value_literal = value

        if value_id is None and value_literal in (None, "", []):
            return None
        return WikiClaimDTO(
            source=candidate.source,
            subject_id=candidate.entity_id,
            subject_label=candidate.label,
            property_id=property_id,
            value_id=value_id,
            value_literal=value_literal,
            value_datatype=value_datatype,
            qualifiers=raw_claim.get("qualifiers", {}) or {},
            references=raw_claim.get("references", []) or [],
        )
