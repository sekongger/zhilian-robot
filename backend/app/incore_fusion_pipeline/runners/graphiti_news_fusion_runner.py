"""Fusion runner that attaches Graphiti news extraction output to the IncCore big graph."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.incore_fusion_pipeline.dto.wikidata_v2_fusion_dto import (
    CanonicalNodeIndexDTO,
    FusionRunResultDTO,
    Neo4jV2ExportPackageDTO,
)
from app.incore_fusion_pipeline.loaders.graphiti_news_neo4j_loader import GraphitiNewsNeo4jLoader
from app.incore_fusion_pipeline.loaders.wikidata_shard_canonical_index_loader import (
    WikidataShardCanonicalIndexLoader,
)
from app.incore_fusion_pipeline.runners.wikidata_v2_fusion_runner import WikidataV2FusionRunner


class GraphitiNewsFusionRunner:
    """Use Wikidata canonical nodes as skeleton and Graphiti output as dynamic news layer."""

    SOURCE_NAMESPACE = "graphiti"

    def __init__(
        self,
        *,
        graphiti_loader: GraphitiNewsNeo4jLoader | None = None,
        canonical_index_loader: WikidataShardCanonicalIndexLoader | None = None,
        fusion_runner: WikidataV2FusionRunner | None = None,
    ) -> None:
        self.graphiti_loader = graphiti_loader or GraphitiNewsNeo4jLoader()
        self.canonical_index_loader = canonical_index_loader or WikidataShardCanonicalIndexLoader()
        self.fusion_runner = fusion_runner or WikidataV2FusionRunner()

    def run_package(
        self,
        *,
        package: Neo4jV2ExportPackageDTO,
        canonical_index: Iterable[CanonicalNodeIndexDTO],
        batch_id: str,
        project: str = "IncCore",
        namespace: str = "IncCore",
    ) -> FusionRunResultDTO:
        """Fuse an already loaded Graphiti package."""

        return self.fusion_runner.run(
            source_nodes=package.nodes,
            source_edges=package.edges,
            canonical_index=canonical_index,
            batch_id=batch_id,
            project=project,
            namespace=namespace,
            source_namespace=self.SOURCE_NAMESPACE,
        )

    def run_from_graphiti_neo4j(
        self,
        *,
        graphiti_neo4j_uri: str,
        graphiti_neo4j_user: str,
        graphiti_neo4j_password: str,
        wikidata_shard_dir: str | Path,
        batch_id: str,
        graphiti_neo4j_database: str | None = None,
        group_id: str | None = None,
        limit: int = 1000,
        edge_limit: int | None = None,
        project: str = "IncCore",
        namespace: str = "IncCore",
    ) -> FusionRunResultDTO:
        """Load Graphiti extracted graph from Neo4j and fuse it into the big graph batch."""

        package = self.graphiti_loader.load_from_neo4j(
            uri=graphiti_neo4j_uri,
            user=graphiti_neo4j_user,
            password=graphiti_neo4j_password,
            database=graphiti_neo4j_database,
            group_id=group_id,
            limit=limit,
            edge_limit=edge_limit,
        )
        canonical_index = self.canonical_index_loader.load_from_dir(wikidata_shard_dir)
        return self.run_package(
            package=package,
            canonical_index=canonical_index,
            batch_id=batch_id,
            project=project,
            namespace=namespace,
        )
