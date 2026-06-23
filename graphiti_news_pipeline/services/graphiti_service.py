import os
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from dotenv import load_dotenv

from crawler.services.canonical_url_service import canonicalize_url, is_traceable_source_url
from graphiti_core import Graphiti
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.embedder import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.nodes import EpisodeType
from services.llm_compat import OpenAIGenericCompatClient

# --- Import schema v1 and v2 models ---
from schemas import knowledge_schema_v2 as schema_v2
from schemas.knowledge_schema import (
    EntityType as CustomEntityType,
    IndustryNode, Region, IndustryActor, Person, Organization, Company,
    Technology, ProductObject, Chunk, Document, DataSource, Index,
    Event, GovernmentPublishPolicyEvent, CompanyCooperationEvent, CompanyFinancingEvent
)


class ChunkedOpenAIEmbedder(OpenAIEmbedder):
    """OpenAI-compatible embedder with provider-safe batch chunking."""

    def __init__(self, *, config: OpenAIEmbedderConfig, batch_size: int) -> None:
        super().__init__(config=config)
        self.batch_size = max(1, batch_size)

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(input_data_list), self.batch_size):
            chunk = input_data_list[start : start + self.batch_size]
            embeddings.extend(await super().create_batch(chunk))
        return embeddings


class GraphitiService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GraphitiService, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            load_dotenv()
            self.schema_version = self._resolve_schema_version()

            # --- Neo4j Configuration ---
            neo4j_uri = os.environ.get('NEO4J_URI')
            neo4j_user = os.environ.get('NEO4J_USER')
            neo4j_password = os.environ.get('NEO4J_PASSWORD')
            if not all([neo4j_uri, neo4j_user, neo4j_password]):
                raise ValueError("NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set in the environment.")

            # --- LLM Configuration (OpenAI-compatible API) ---
            llm_api_key = os.environ.get('OPENAI_API_KEY')
            llm_base_url = os.environ.get('OPENAI_API_BASE')
            llm_model = os.environ.get('OPENAI_MODEL')
            llm_small_model = os.environ.get('OPENAI_SMALL_MODEL', llm_model)

            if not all([llm_api_key, llm_base_url, llm_model]):
                raise ValueError(
                    "OPENAI_API_KEY, OPENAI_API_BASE, and OPENAI_MODEL must be set for LLM API."
                )

            llm_config = LLMConfig(
                api_key=llm_api_key,
                base_url=llm_base_url,
                model=llm_model,
                small_model=llm_small_model,
                temperature=0,
            )
            llm_client = OpenAIGenericCompatClient(config=llm_config)

            # --- Embedding Configuration (reserved for custom provider) ---
            # Fill these in when your embedding endpoint/model is finalized:
            # EMBEDDING_API_KEY, EMBEDDING_API_BASE, EMBEDDING_MODEL, EMBEDDING_DIM
            embedding_api_key = os.environ.get('EMBEDDING_API_KEY', llm_api_key)
            embedding_base_url = os.environ.get('EMBEDDING_API_BASE', llm_base_url)
            embedding_model = os.environ.get('EMBEDDING_MODEL', 'text-embedding-3-small')
            embedding_dim_raw = os.environ.get('EMBEDDING_DIM')
            embedding_batch_size = int(os.environ.get('EMBEDDING_BATCH_SIZE', '10'))

            embedder_kwargs = {
                'api_key': embedding_api_key,
                'base_url': embedding_base_url,
                'embedding_model': embedding_model,
            }
            if embedding_dim_raw:
                embedder_kwargs['embedding_dim'] = int(embedding_dim_raw)

            embedder = ChunkedOpenAIEmbedder(
                config=OpenAIEmbedderConfig(**embedder_kwargs),
                batch_size=embedding_batch_size,
            )
            if os.environ.get('EMBEDDING_MODEL') is None:
                logging.warning(
                    "EMBEDDING_MODEL is not set. Using placeholder default "
                    "'text-embedding-3-small'. Configure EMBEDDING_* env vars later."
                )

            cross_encoder = OpenAIRerankerClient(config=llm_config)

            # --- Initialize Graphiti with injected clients ---
            self.graphiti = Graphiti(
                neo4j_uri,
                neo4j_user,
                neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=cross_encoder,
            )

            self.db_initialized = False
            self.initialized = True
            logging.info(
                "Graphiti Service configured with custom LLM API. "
                f"llm_model={llm_model}, llm_base={llm_base_url}, embedding_model={embedding_model}, "
                f"embedding_batch_size={embedding_batch_size}, "
                f"schema_version={self.schema_version}"
            )

    @staticmethod
    def _resolve_schema_version() -> str:
        raw = str(os.getenv("GRAPHITI_SCHEMA_VERSION", "v1")).strip().lower()
        if raw in {"v2", "0422", "latest", "new"}:
            return "v2"
        return "v1"

    @staticmethod
    def _build_entity_types_v1() -> dict[str, type]:
        return {
            # Entities
            CustomEntityType.INDUSTRY_NODE.value: IndustryNode,
            CustomEntityType.REGION.value: Region,
            CustomEntityType.COMPANY.value: Company,
            CustomEntityType.ORGANIZATION.value: Organization,
            CustomEntityType.PERSON.value: Person,
            CustomEntityType.TECHNOLOGY.value: Technology,
            CustomEntityType.PRODUCT_OBJECT.value: ProductObject,
            CustomEntityType.CHUNK.value: Chunk,
            CustomEntityType.DOCUMENT.value: Document,
            CustomEntityType.DATA_SOURCE.value: DataSource,
            CustomEntityType.INDEX.value: Index,
            # Events
            CustomEntityType.EVENT.value: Event,
            CustomEntityType.GOVERNMENT_PUBLISH_POLICY_EVENT.value: GovernmentPublishPolicyEvent,
            CustomEntityType.COMPANY_COOPERATION_EVENT.value: CompanyCooperationEvent,
            CustomEntityType.COMPANY_FINANCING_EVENT.value: CompanyFinancingEvent,
        }

    @staticmethod
    def _build_entity_types_v2() -> dict[str, type]:
        return {
            schema_v2.EntityType.ECONOMIC_SECTOR.value: schema_v2.EconomicSector,
            schema_v2.EntityType.INDUSTRY_GROUP.value: schema_v2.IndustryGroup,
            schema_v2.EntityType.INDUSTRY.value: schema_v2.Industry,
            schema_v2.EntityType.PRODUCT_TERM.value: schema_v2.ProductTerm,
            schema_v2.EntityType.PRODUCT.value: schema_v2.Product,
            schema_v2.EntityType.PRODUCT_MODEL.value: schema_v2.ProductModel,
            schema_v2.EntityType.ENTERPRISE.value: schema_v2.Enterprise,
            schema_v2.EntityType.TECHNOLOGY.value: schema_v2.Technology,
            schema_v2.EntityType.PATENT.value: schema_v2.Patent,
            schema_v2.EntityType.ORGANIZATION.value: schema_v2.Organization,
            schema_v2.EntityType.PERSON.value: schema_v2.Person,
            schema_v2.EntityType.REGION.value: schema_v2.Region,
            schema_v2.EntityType.POLICY.value: schema_v2.Policy,
            schema_v2.EntityType.INDEX.value: schema_v2.Index,
            schema_v2.EntityType.DATA_SOURCE.value: schema_v2.DataSource,
            schema_v2.EntityType.DOCUMENT.value: schema_v2.Document,
            schema_v2.EntityType.CHUNK.value: schema_v2.Chunk,
            schema_v2.EntityType.ENTERPRISE_EVENT.value: schema_v2.EnterpriseEvent,
            schema_v2.EntityType.ORGANIZATION_EVENT.value: schema_v2.OrganizationEvent,
        }

    def _build_entity_types(self) -> dict[str, type]:
        if self.schema_version == "v2":
            return self._build_entity_types_v2()
        return self._build_entity_types_v1()

    async def initialize_database(self):
        """
        Initializes the graph database with necessary indices and constraints.
        Should be run once.
        """
        if not self.db_initialized:
            await self.graphiti.build_indices_and_constraints()
            self.db_initialized = True
            logging.info("Graph database indices and constraints are set up.")
            return {"status": "success", "message": "Database initialized successfully."}
        return {"status": "skipped", "message": "Database was already initialized."}

    async def _update_episode_metadata(
        self,
        episode_uuid: str,
        episode_metadata: dict[str, Any],
    ) -> None:
        """
        Update custom metadata on Episodic nodes without changing graphiti-core schema.
        """
        if not episode_metadata:
            return

        query = """
        MATCH (ep:Episodic {uuid: $episode_uuid})
        SET
            ep.title = coalesce($title, ep.title),
            ep.publish_time = coalesce($publish_time, ep.publish_time),
            ep.news_source = coalesce($news_source, ep.news_source),
            ep.news_url = coalesce($news_url, ep.news_url),
            ep.group_id = coalesce($group_id, ep.group_id),
            ep.fusion_batch_id = coalesce($fusion_batch_id, ep.fusion_batch_id),
            ep.raw_text = coalesce($raw_text, ep.raw_text),
            ep.structured_facts_json = coalesce($structured_facts_json, ep.structured_facts_json),
            ep.ingested_at = coalesce(ep.ingested_at, ep.created_at)
        """
        await self.graphiti.driver.execute_query(
            query,
            episode_uuid=episode_uuid,
            title=episode_metadata.get("title"),
            publish_time=episode_metadata.get("publish_time"),
            news_source=episode_metadata.get("news_source"),
            news_url=episode_metadata.get("news_url"),
            group_id=episode_metadata.get("group_id"),
            fusion_batch_id=episode_metadata.get("fusion_batch_id"),
            raw_text=episode_metadata.get("raw_text"),
            structured_facts_json=episode_metadata.get("structured_facts_json"),
        )

    async def _find_existing_episode_by_url(self, news_url: str) -> dict[str, Any] | None:
        query = """
        MATCH (ep:Episodic)
        WHERE ep.news_url = $news_url
        RETURN
            ep.uuid AS uuid,
            coalesce(ep.publish_time, ep.valid_at, ep.created_at) AS valid_at,
            ep.created_at AS created_at
        ORDER BY coalesce(ep.publish_time, ep.valid_at, ep.created_at) DESC
        LIMIT 1
        """
        records, _, _ = await self.graphiti.driver.execute_query(query, news_url=news_url)
        if not records:
            return None
        return {
            "uuid": records[0]["uuid"],
            "valid_at": records[0]["valid_at"],
            "created_at": records[0]["created_at"],
        }

    async def _find_existing_episode_by_title_source_day(
        self,
        title: str,
        news_source: str,
        publish_time: datetime,
    ) -> dict[str, Any] | None:
        query = """
        MATCH (ep:Episodic)
        WHERE coalesce(ep.title, ep.name, '') = $title
          AND coalesce(ep.news_source, '') = $news_source
          AND date(coalesce(ep.publish_time, ep.valid_at, ep.created_at)) = date($publish_time)
        RETURN
            ep.uuid AS uuid,
            coalesce(ep.publish_time, ep.valid_at, ep.created_at) AS valid_at,
            ep.created_at AS created_at
        ORDER BY coalesce(ep.publish_time, ep.valid_at, ep.created_at) DESC
        LIMIT 1
        """
        records, _, _ = await self.graphiti.driver.execute_query(
            query,
            title=title,
            news_source=news_source,
            publish_time=publish_time,
        )
        if not records:
            return None
        return {
            "uuid": records[0]["uuid"],
            "valid_at": records[0]["valid_at"],
            "created_at": records[0]["created_at"],
        }

    @staticmethod
    def _normalize_episode_metadata(
        episode_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metadata = dict(episode_metadata or {})

        title = str(metadata.get("title") or "").strip()
        metadata["title"] = title if title else None

        source = str(metadata.get("news_source") or "").strip()
        metadata["news_source"] = source if source else None

        raw_text = str(metadata.get("raw_text") or "").strip()
        metadata["raw_text"] = raw_text if raw_text else None

        structured_facts_json = str(metadata.get("structured_facts_json") or "").strip()
        metadata["structured_facts_json"] = structured_facts_json if structured_facts_json else None

        group_id = str(metadata.get("group_id") or "").strip()
        metadata["group_id"] = group_id if group_id else None

        fusion_batch_id = str(metadata.get("fusion_batch_id") or group_id or "").strip()
        metadata["fusion_batch_id"] = fusion_batch_id if fusion_batch_id else None

        raw_url = str(metadata.get("news_url") or "").strip()
        normalized_url = canonicalize_url(raw_url) if raw_url else ""
        metadata["news_url"] = normalized_url if normalized_url and is_traceable_source_url(normalized_url) else None
        return metadata

    @staticmethod
    def _build_existing_episode_stub(existing: dict[str, Any]):
        return SimpleNamespace(
            episode=SimpleNamespace(
                uuid=existing["uuid"],
                valid_at=existing.get("valid_at"),
                created_at=existing.get("created_at"),
            ),
            nodes=[],
        )

    async def add_text_episode(
        self,
        text: str,
        name: str = "Unnamed Episode",
        reference_time: datetime | None = None,
        source_description: str = "API text input",
        episode_metadata: dict[str, Any] | None = None,
        group_id: str | None = None,
    ) -> tuple[Any, bool]:
        """
        Adds a text episode to the graph, providing our custom entity schema
        to guide the extraction process.
        """
        metadata = self._normalize_episode_metadata(episode_metadata)
        graphiti_group_id = (group_id or metadata.get("group_id") or metadata.get("fusion_batch_id") or "").strip() or None
        if graphiti_group_id:
            metadata["group_id"] = graphiti_group_id
            metadata["fusion_batch_id"] = metadata.get("fusion_batch_id") or graphiti_group_id

        news_url = metadata.get("news_url")
        existing_episode: dict[str, Any] | None = None
        if news_url:
            existing_episode = await self._find_existing_episode_by_url(news_url)

        title_for_dedup = metadata.get("title") or name.strip()
        source_for_dedup = metadata.get("news_source")
        publish_time_for_dedup = metadata.get("publish_time") or reference_time
        if (
            existing_episode is None
            and title_for_dedup
            and source_for_dedup
            and isinstance(publish_time_for_dedup, datetime)
        ):
            existing_episode = await self._find_existing_episode_by_title_source_day(
                title_for_dedup,
                source_for_dedup,
                publish_time_for_dedup,
            )

        if existing_episode is not None:
            await self._update_episode_metadata(existing_episode["uuid"], metadata)
            return self._build_existing_episode_stub(existing_episode), True

        entity_types = self._build_entity_types()

        results = await self.graphiti.add_episode(
            name=name,
            episode_body=text,
            source=EpisodeType.text,
            source_description=source_description,
            reference_time=reference_time or datetime.now(timezone.utc),
            group_id=graphiti_group_id,
            entity_types=entity_types  # Pass our custom schema here
        )
        if metadata:
            await self._update_episode_metadata(results.episode.uuid, metadata)

        return results, False

    async def sync_common_sense_anchors(self, anchors: list[dict[str, Any]]) -> dict[str, int]:
        """Idempotently mirror common-sense nodes into Graphiti as anchors."""

        synced = 0
        for raw_anchor in anchors or []:
            anchor = dict(raw_anchor or {})
            anchor_id = str(anchor.get("anchor_id") or anchor.get("id") or anchor.get("canonicalGraphId") or "").strip()
            name = str(anchor.get("name") or "").strip()
            if not anchor_id or not name:
                continue
            aliases = anchor.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            properties_json = json.dumps(anchor.get("properties") or {}, ensure_ascii=False, default=str)
            await self.graphiti.driver.execute_query(
                """
                MERGE (a:CommonSenseAnchor {anchor_id: $anchor_id})
                SET
                    a.id = $anchor_id,
                    a.canonicalGraphId = $anchor_id,
                    a.type_name = $type_name,
                    a.name = $name,
                    a.aliases = $aliases,
                    a.description = $description,
                    a.source_graph = $source_graph,
                    a.source_version = $source_version,
                    a.properties_json = $properties_json,
                    a.updated_at = datetime()
                RETURN a.anchor_id AS anchor_id
                """,
                anchor_id=anchor_id,
                type_name=anchor.get("type_name") or anchor.get("type") or "Unknown",
                name=name,
                aliases=[str(item) for item in aliases if item],
                description=str(anchor.get("description") or ""),
                source_graph=str(anchor.get("source_graph") or "incore_common_neo4j"),
                source_version=anchor.get("source_version"),
                properties_json=properties_json,
            )
            synced += 1
        return {"synced": synced, "skipped": max(0, len(anchors or []) - synced)}

    async def link_news_entities_to_anchors(self, decisions: list[dict[str, Any]]) -> dict[str, int]:
        """Write entity-to-anchor link decisions into Graphiti."""

        stats = {"refersTo": 0, "candidateRefersTo": 0, "unresolved": 0}
        for raw_decision in decisions or []:
            decision = dict(raw_decision or {})
            relation = str(decision.get("decision") or "unresolved")
            if relation not in stats:
                relation = "unresolved"
            stats[relation] += 1
            if relation not in {"refersTo", "candidateRefersTo"} or not decision.get("candidate_anchor_id"):
                await self.graphiti.driver.execute_query(
                    """
                    MATCH (entity)
                    WHERE coalesce(entity.uuid, entity.id, elementId(entity)) = $news_entity_id
                    SET
                        entity.linkDecision = 'unresolved',
                        entity.linkReason = $reason,
                        entity.linkGroupId = $group_id,
                        entity.matchScore = $match_score,
                        entity.matchMethod = $match_method
                    RETURN count(entity) AS updated
                    """,
                    news_entity_id=decision.get("news_entity_id"),
                    reason=decision.get("reason"),
                    group_id=decision.get("group_id"),
                    match_score=decision.get("match_score") or 0.0,
                    match_method=decision.get("match_method") or "none",
                )
                continue
            await self._write_entity_anchor_link(decision, relation)
        return stats

    async def _write_entity_anchor_link(self, decision: dict[str, Any], relation: str) -> None:
        await self.graphiti.driver.execute_query(
            f"""
            MATCH (entity)
            WHERE coalesce(entity.uuid, entity.id, elementId(entity)) = $news_entity_id
            MATCH (anchor:CommonSenseAnchor {{anchor_id: $candidate_anchor_id}})
            MERGE (entity)-[r:{relation}]->(anchor)
            SET
                r.matchScore = $match_score,
                r.matchMethod = $match_method,
                r.reason = $reason,
                r.group_id = $group_id,
                r.updated_at = datetime(),
                entity.canonicalGraphId = CASE
                    WHEN $decision = 'refersTo' THEN $candidate_anchor_id
                    ELSE entity.canonicalGraphId
                END,
                entity.matchScore = $match_score,
                entity.matchMethod = $match_method
            RETURN count(r) AS linked
            """,
            news_entity_id=decision.get("news_entity_id"),
            candidate_anchor_id=decision.get("candidate_anchor_id"),
            match_score=decision.get("match_score") or 0.0,
            match_method=decision.get("match_method") or "none",
            reason=decision.get("reason") or "",
            group_id=decision.get("group_id") or "",
            decision=relation,
        )

    async def get_anchor_link_stats(self, group_id: str) -> dict[str, Any]:
        records, _, _ = await self.graphiti.driver.execute_query(
            """
            MATCH (ep:Episodic)-[mention_rel]-(entity)
            WHERE type(mention_rel) IN ['mentions', 'MENTIONS']
              AND (ep.group_id = $group_id OR ep.fusion_batch_id = $group_id)
            WITH DISTINCT entity
            OPTIONAL MATCH (entity)-[rt:refersTo]->(:CommonSenseAnchor)
            OPTIONAL MATCH (entity)-[crt:candidateRefersTo]->(:CommonSenseAnchor)
            RETURN
                count(DISTINCT entity) AS entity_count,
                count(DISTINCT rt) AS refersTo,
                count(DISTINCT crt) AS candidateRefersTo,
                count(DISTINCT CASE
                    WHEN rt IS NULL AND crt IS NULL THEN entity
                    ELSE NULL
                END) AS unresolved
            """,
            group_id=group_id,
        )
        row = records[0] if records else {}
        return {
            "group_id": group_id,
            "entity_count": int(row.get("entity_count") or 0),
            "refersTo": int(row.get("refersTo") or 0),
            "candidateRefersTo": int(row.get("candidateRefersTo") or 0),
            "unresolved": int(row.get("unresolved") or 0),
        }

    async def search_graph(self, query: str, center_node_uuid: str = None):
        """
        Performs a hybrid search on the graph for a given query.
        """
        results = await self.graphiti.search(query, center_node_uuid=center_node_uuid)

        return [
            {
                "uuid": str(result.uuid),
                "fact": result.fact,
                "source_node_uuid": str(result.source_node_uuid),
                "target_node_uuid": str(result.target_node_uuid),
                "valid_at": result.valid_at.isoformat() if result.valid_at else None,
                "invalid_at": result.invalid_at.isoformat() if result.invalid_at else None,
            } for result in results
        ]

    async def close_connection(self):
        """Closes the connection to the database."""
        await self.graphiti.close()
        logging.info("Graphiti connection closed.")


# Singleton instance for the application
graphiti_service = GraphitiService()
