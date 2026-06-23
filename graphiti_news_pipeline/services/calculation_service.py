import asyncio
import logging
import os
import re
from datetime import datetime, timezone, timedelta

from .graphiti_service import graphiti_service
from .entity_heat_service import EntityHeatRankingService

# A simple regex to validate UUID format to mitigate risks of f-string injection
UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
INVESTMENT_RELATION_NAMES = [
    "INVESTS_IN",
    "MADE_STRATEGIC_INVESTMENT_IN",
    "INVESTED_IN",
    "STRATEGIC_INVESTMENT",
    "INVEST",
    "INVESTMENT",
    "INVEST_IN",
    "STRATEGIC_INVEST",
    "STRATEGIC_INVESTMENT_IN",
    "投资",
    "战略投资",
]
FINANCING_EVENT_LABELS = [
    "CompanyFinancingEvent",
    "EnterpriseEvent",
]
PAGERANK_CALCULATION_LOCK = asyncio.Lock()
COMMUNITY_CALCULATION_LOCK = asyncio.Lock()
NEWS_HOTNESS_CALCULATION_LOCK = asyncio.Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float, min_value: float | None = None, max_value: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        value = default
    else:
        try:
            value = float(raw)
        except ValueError:
            logging.warning("Invalid %s=%s; fallback to %.4f", name, raw, default)
            value = default

    if min_value is not None and value < min_value:
        logging.warning("%s below min %.4f; clamped from %.4f", name, min_value, value)
        value = min_value
    if max_value is not None and value > max_value:
        logging.warning("%s above max %.4f; clamped from %.4f", name, max_value, value)
        value = max_value
    return value


def _load_investment_relation_names() -> list[str]:
    configured = os.getenv("INVESTMENT_RELATION_NAMES", "")
    names = list(INVESTMENT_RELATION_NAMES)
    if configured.strip():
        names.extend([item.strip() for item in configured.split(",") if item.strip()])
    # Preserve order while deduplicating.
    return list(dict.fromkeys(names))


MOMENTUM_USE_RELATION_FALLBACK = _env_bool("MOMENTUM_USE_RELATION_FALLBACK", default=False)
NEWS_HOTNESS_IMPACT_WEIGHT = _env_float("NEWS_HOTNESS_IMPACT_WEIGHT", default=0.1, min_value=0.0)
ENTITY_HEAT_RANKING_LIMIT_PER_TYPE = int(os.getenv("ENTITY_HEAT_RANKING_LIMIT_PER_TYPE", "50"))
_INVESTMENT_RELATION_NAMES_ACTIVE = _load_investment_relation_names()


async def _has_enough_entity_graph(driver) -> bool:
    """
    Guard against running GDS algorithms on empty/near-empty graphs.
    """
    count_query = """
    MATCH (n:Entity)
    WITH count(n) AS entity_count
    OPTIONAL MATCH (:Entity)-[r]-(:Entity)
    RETURN entity_count, count(r) AS relationship_count
    """
    records, _, _ = await driver.execute_query(count_query)
    if not records:
        return False

    entity_count = int(records[0]["entity_count"] or 0)
    relationship_count = int(records[0]["relationship_count"] or 0)
    if entity_count < 2 or relationship_count < 1:
        logging.warning(
            "Skip graph calculation due to insufficient data: entity_count=%s relationship_count=%s",
            entity_count,
            relationship_count,
        )
        return False
    return True


async def calculate_all_after_ingest(
    entity_uuids: list[str],
    episode_uuid: str | None = None,
) -> None:
    """
    Serially run all calculation steps after a new episode ingest.
    """
    unique_entity_uuids = []
    seen = set()
    for entity_uuid in entity_uuids:
        if not entity_uuid or entity_uuid in seen:
            continue
        seen.add(entity_uuid)
        unique_entity_uuids.append(entity_uuid)

    logging.info(
        "Post-ingest calculation pipeline started. entities=%s episode_uuid=%s",
        len(unique_entity_uuids),
        episode_uuid,
    )

    for entity_uuid in unique_entity_uuids:
        await calculate_and_store_momentum(entity_uuid)

    await calculate_and_store_pagerank()
    await calculate_and_store_communities()
    await calculate_and_store_news_hotness()
    await calculate_and_store_entity_heat_rankings(period_type="daily")
    await calculate_and_store_entity_heat_rankings(period_type="weekly")
    logging.info("Post-ingest calculation pipeline completed.")

async def calculate_and_store_momentum(entity_uuid: str):
    """
    一个完整的计算任务：从图数据库中查询数据，计算实体的动量，然后将结果存回。
    
    动量计算逻辑 (V5):
    - 过去30天内，每被一篇资讯提及一次，得1分。
    - 过去90天内，每参与一次投资行为（无论投出或被投），得5分。
      投资行为默认按事件节点模式统计：
      1) 事件节点模式: (:CompanyFinancingEvent|:EnterpriseEvent)-[:SUBJECT|OBJECT]->(:Entity)
      2) 可选回退：若启用 MOMENTUM_USE_RELATION_FALLBACK 且无事件节点，再使用实体关系模式
    """
    logging.info(f"后台任务开始: 为实体 {entity_uuid} 计算动量...")

    if not UUID_REGEX.match(entity_uuid):
        logging.error(f"无效的 UUID 格式: {entity_uuid}")
        return

    try:
        driver = graphiti_service.graphiti.driver
        
        # 在Python中准备好时间参数，避免时区问题
        time_30_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        time_90_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        # 1. 查询近期提及次数
        mentions_query = """
        MATCH (ep:Episodic)-[:MENTIONS]->(n:Entity {uuid: $uuid})
        WHERE coalesce(ep.publish_time, ep.valid_at, ep.created_at) >= $start_date
        RETURN count(DISTINCT ep) AS mention_count
        """
        mentions_params = {"uuid": entity_uuid, "start_date": time_30_days_ago}
        mentions_records, _, _ = await driver.execute_query(mentions_query, **mentions_params)
        mention_score = mentions_records[0]["mention_count"] if mentions_records and mentions_records[0]["mention_count"] else 0
        logging.info(f"Mention score: {mention_score}")
        
        # 2. 查询近期投资次数（事件节点口径）
        investments_query = """
        MATCH (n:Entity {uuid: $uuid})
        OPTIONAL MATCH (event)-[:SUBJECT|OBJECT]->(n)
        WHERE any(label IN labels(event) WHERE label IN $event_labels)
          AND coalesce(event.publishTime, event.valid_at, event.created_at) >= $start_date
        RETURN count(DISTINCT event) AS event_count
        """
        investments_params = {
            "uuid": entity_uuid,
            "start_date": time_90_days_ago,
            "event_labels": FINANCING_EVENT_LABELS,
        }
        investments_records, _, _ = await driver.execute_query(investments_query, **investments_params)
        event_count = investments_records[0]["event_count"] if investments_records and investments_records[0]["event_count"] else 0

        relation_count = 0
        if MOMENTUM_USE_RELATION_FALLBACK and event_count == 0:
            relation_query = """
            MATCH (n:Entity {uuid: $uuid})-[r]-(other:Entity)
            WHERE other.uuid <> n.uuid
              AND coalesce(r.name, type(r)) IN $relation_names
              AND coalesce(r.valid_at, r.created_at) >= $start_date
            RETURN count(DISTINCT r) AS relation_count
            """
            relation_records, _, _ = await driver.execute_query(
                relation_query,
                uuid=entity_uuid,
                start_date=time_90_days_ago,
                relation_names=_INVESTMENT_RELATION_NAMES_ACTIVE,
            )
            relation_count = (
                relation_records[0]["relation_count"]
                if relation_records and relation_records[0]["relation_count"]
                else 0
            )

        investment_count = event_count if event_count > 0 else relation_count
        investment_score = investment_count * 5
        logging.info(
            f"Investment count: {investment_count} "
            f"(event_count={event_count}, relation_count={relation_count}), "
            f"investment score: {investment_score}"
        )

        # 3. 计算总分
        final_score = float(mention_score + investment_score)
        
        # 4. 将结果写回图数据库
        update_query = """
        MATCH (n {uuid: $uuid})
        SET n.momentum_score = $score, n.momentum_updated_at = $updated_at
        """
        update_params = {
            "uuid": entity_uuid,
            "score": final_score,
            "updated_at": datetime.now(timezone.utc)
        }
        await driver.execute_query(update_query, **update_params)
        
        logging.info(f"后台任务完成: 实体 {entity_uuid} 的动量分计算为: {final_score}")

    except Exception as e:
        logging.error(f"为实体 {entity_uuid} 计算动量时发生错误: {e}", exc_info=True)


async def calculate_and_store_pagerank():
    """
    【最终版】计算图中所有实体的 PageRank，并将其作为属性写回。
    使用 Cypher 投影以获得最佳的稳定性和精确性。
    """
    logging.info("后台任务开始: 【最终版】计算全图 PageRank...")
    if PAGERANK_CALCULATION_LOCK.locked():
        logging.warning("PageRank calculation is already running. Waiting for current task to finish.")

    async with PAGERANK_CALCULATION_LOCK:
        driver = graphiti_service.graphiti.driver
        graph_name = "pagerank_graph"
        if not await _has_enough_entity_graph(driver):
            return

        # 1. 清理可能存在的旧图
        try:
            await driver.execute_query(f"CALL gds.graph.drop('{graph_name}', false) YIELD graphName;")
        except Exception:
            pass  # 忽略图不存在的错误

        try:
            # 2. 使用 Cypher 投影创建内存图，精确指定节点和关系（新版：包含所有关系类型）
            project_query = f"""
            CALL gds.graph.project.cypher(
                '{graph_name}',
                'MATCH (n:Entity) RETURN id(n) AS id, labels(n) as labels',
                'MATCH (source:Entity)-[r]-(target:Entity)
                 WHERE id(source) <> id(target)
                 RETURN id(source) AS source, id(target) AS target, type(r) as type
                 UNION
                 MATCH (source:Entity)-[r]-(target:Entity)
                 WHERE id(source) <> id(target)
                 RETURN id(target) AS source, id(source) AS target, type(r) as type'
            ) YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            await driver.execute_query(project_query)
            logging.info(f"内存图 '{graph_name}' 投影成功！")

            # 3. 在投射的图上执行 PageRank 算法，并将结果写回
            write_query = f"""
            CALL gds.pageRank.write(
                '{graph_name}',
                {{
                    writeProperty: 'pageRank'
                }}
            )
            YIELD nodePropertiesWritten
            RETURN nodePropertiesWritten
            """
            await driver.execute_query(write_query)

            logging.info("后台任务完成: PageRank 计算并写回成功。")

        except Exception as e:
            logging.error(f"【最终版】计算 PageRank 时发生错误: {e}", exc_info=True)
        finally:
            # 4. 清理内存图
            try:
                await driver.execute_query(f"CALL gds.graph.drop('{graph_name}', false) YIELD graphName;")
                logging.info(f"内存图 '{graph_name}' 已清理。")
            except Exception:
                pass # 忽略清理时可能发生的错误

async def calculate_and_store_communities():
    """
    【最终版】使用Louvain算法计算图中的社群，并将社群ID作为属性写回到每个实体节点。
    使用 Cypher 投影以获得最佳的稳定性和精确性。
    """
    logging.info("后台任务开始: 【最终版】计算全图社群 (Louvain)...")
    if COMMUNITY_CALCULATION_LOCK.locked():
        logging.warning("Community calculation is already running. Waiting for current task to finish.")

    async with COMMUNITY_CALCULATION_LOCK:
        driver = graphiti_service.graphiti.driver
        graph_name = "community_graph"
        if not await _has_enough_entity_graph(driver):
            return

        # 1. 清理可能存在的旧图
        try:
            await driver.execute_query(f"CALL gds.graph.drop('{graph_name}', false) YIELD graphName;")
        except Exception:
            pass  # 忽略图不存在的错误

        try:
            # 2. 使用 Cypher 投影创建内存图（新版：包含所有关系类型）
            project_query = f"""
            CALL gds.graph.project.cypher(
                '{graph_name}',
                'MATCH (n:Entity) RETURN id(n) AS id, labels(n) as labels',
                'MATCH (source:Entity)-[r]-(target:Entity)
                 WHERE id(source) <> id(target)
                 RETURN id(source) AS source, id(target) AS target, type(r) as type
                 UNION
                 MATCH (source:Entity)-[r]-(target:Entity)
                 WHERE id(source) <> id(target)
                 RETURN id(target) AS source, id(source) AS target, type(r) as type'
            ) YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """
            await driver.execute_query(project_query)
            logging.info(f"内存图 '{graph_name}' 投影成功！")

            # 3. 在投射的图上执行 Louvain 算法，并将结果写回
            write_query = f"""
            CALL gds.louvain.write(
                '{graph_name}',
                {{
                    writeProperty: 'communityId'
                }}
            )
            YIELD communityCount, nodePropertiesWritten
            RETURN communityCount, nodePropertiesWritten
            """
            records, _, _ = await driver.execute_query(write_query)
            community_count = records[0]["communityCount"] if records else 0
            logging.info(f"后台任务完成: 社群发现计算成功，共发现 {community_count} 个社群。")

        except Exception as e:
            logging.error(f"【最终版】计算社群时发生错误: {e}", exc_info=True)
        finally:
            # 4. 清理内存图
            try:
                await driver.execute_query(f"CALL gds.graph.drop('{graph_name}', false) YIELD graphName;")
                logging.info(f"内存图 '{graph_name}' 已清理。")
            except Exception:
                pass # 忽略清理时可能发生的错误


async def calculate_and_store_news_hotness(
    episode_uuid: str | None = None,
    since_days: int | None = None,
):
    """
    计算所有资讯（Episodic节点）的热度分数，并将其写回图数据库。
    热度分 = 新颖度分 + (影响力分 * impact_weight)
    - 新颖度分: 基于文章发布时间，7天内有效，分数从7到1。
    - 影响力分: 基于文章提及的所有实体的动量分(momentum_score)之和。
    - impact_weight: 由 NEWS_HOTNESS_IMPACT_WEIGHT 环境变量配置，默认 0.1。
    """
    scope_desc = "all episodic nodes"
    if episode_uuid:
        scope_desc = f"episode_uuid={episode_uuid}"
    elif since_days and since_days > 0:
        scope_desc = f"episodes in last {since_days} day(s)"

    logging.info(
        "后台任务开始: 计算资讯热度分数. scope=%s impact_weight=%.4f",
        scope_desc,
        NEWS_HOTNESS_IMPACT_WEIGHT,
    )
    if NEWS_HOTNESS_CALCULATION_LOCK.locked():
        logging.warning("News hotness calculation is already running. Waiting for current task to finish.")

    async with NEWS_HOTNESS_CALCULATION_LOCK:
        driver = graphiti_service.graphiti.driver
        where_clauses = ["coalesce(ep.publish_time, ep.valid_at, ep.created_at) IS NOT NULL"]
        params: dict[str, object] = {"impact_weight": NEWS_HOTNESS_IMPACT_WEIGHT}

        if episode_uuid:
            where_clauses.append("ep.uuid = $episode_uuid")
            params["episode_uuid"] = episode_uuid
        elif since_days and since_days > 0:
            params["since_time"] = datetime.now(timezone.utc) - timedelta(days=since_days)
            where_clauses.append("coalesce(ep.publish_time, ep.valid_at, ep.created_at) >= $since_time")

        query = f"""
        // 1. 匹配指定范围内资讯节点
        MATCH (ep:Episodic)
        WHERE {' AND '.join(where_clauses)}

        // 2. 计算新颖度分（基于发布时刻，限制在[0, 7]）
        WITH ep, duration.inDays(coalesce(ep.publish_time, ep.valid_at, ep.created_at), datetime()).days AS ageInDays
        WITH ep, CASE
            WHEN ageInDays < 0 THEN 7.0
            WHEN ageInDays < 7 THEN 7.0 - toFloat(ageInDays)
            ELSE 0.0
        END AS recencyScore

        // 3. 计算影响力分（去重后的被提及实体）
        OPTIONAL MATCH (ep)-[:MENTIONS]->(entity:Entity)
        WITH ep, recencyScore, collect(DISTINCT entity) AS mentioned_entities
        WITH ep, recencyScore,
            reduce(impact = 0.0, e IN mentioned_entities | impact + coalesce(e.momentum_score, 0.0)) AS impactScore

        // 4. 计算最终热度分（影响力系数可配置）
        WITH ep, recencyScore, impactScore, (recencyScore + (impactScore * $impact_weight)) AS hotnessScore

        // 5. 将结果写回节点
        SET ep.news_hotness_score = hotnessScore,
            ep.news_hotness_updated_at = datetime()

        RETURN count(ep) AS updatedCount
        """

        try:
            records, _, _ = await driver.execute_query(query, **params)
            updated_count = records[0]["updatedCount"] if records else 0
            logging.info(
                "后台任务完成: 成功为 %s 条资讯计算并存储热度分数。scope=%s",
                updated_count,
                scope_desc,
            )
        except Exception as e:
            logging.error(f"计算资讯热度分数时发生错误: {e}", exc_info=True)


async def calculate_and_store_entity_heat_rankings(
    *,
    period_type: str,
    as_of: str | datetime | None = None,
    entity_type: str | None = None,
    limit_per_type: int | None = None,
) -> dict:
    """
    Generate daily/weekly entity heat ranking snapshots as a pipeline byproduct.
    """
    service = EntityHeatRankingService(graphiti_service.graphiti.driver)
    return await service.generate_and_store_rankings(
        period_type=period_type,
        as_of=as_of,
        entity_type=entity_type,
        limit_per_type=limit_per_type or ENTITY_HEAT_RANKING_LIMIT_PER_TYPE,
    )
