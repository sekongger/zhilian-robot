"""
实体操作相关API路由
提供实体监控、研判溯源、AI简报生成等功能
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List
from datetime import datetime
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/entity-actions", tags=["Entity Actions"])


def generate_smart_summary(entity_name: str, article_title: str, article_content: str = None) -> str:
    """
    使用DeepSeek API生成智能摘要
    
    Args:
        entity_name: 实体名称
        article_title: 文章标题
        article_content: 文章内容（可选）
        
    Returns:
        智能生成的简短摘要
    """
    try:
        from app.nlp.llm import LLMProcessor
        
        llm = LLMProcessor()
        if not llm.client:
            # 如果LLM不可用，返回标题摘要
            return article_title[:30] + ('...' if len(article_title) > 30 else '')
        
        # 构建prompt - 强调主体动作的明确性
        content_snippet = article_content[:400] if article_content else article_title
        
        prompt = f"""请提取与"{entity_name}"相关的最新动态，生成一句信息明确的摘要。

【新闻】
标题：{article_title}
内容：{content_snippet}

【输出要求】
1. 结构：主体 + 具体动作 + 对象/结果
2. 长度：12-20字
3. 主体明确：必须明确说明是谁（具体公司/产品名称），禁止使用"该公司"、"该产品"等模糊指代
4. 动作具体：使用"发布了"、"宣布"、"完成"、"获得"、"展示了"、"接受了"等明确动词
5. 关联性：如果{entity_name}不是主体，说明其在事件中的具体作用

【正确示例】
✓ "Figure AI 发布了新的演示视频"（主体明确+动作清晰+对象具体）
✓ "Unitree CEO 接受了 TechCrunch 采访"（人物+动作+媒体）
✓ "绿的谐波完成 3 亿元 C 轮融资"（公司+完成+具体金额）
✓ "北京批准 Robotaxi 无安全员路测"（地区+批准+具体项目）

【错误示例】
✗ "该公司完成融资"（主体模糊）
✗ "应用于人形机器人"（缺少主语和动作）
✗ "关于供应链问题"（信息不完整）

直接输出："""

        response = llm.client.chat.completions.create(
            model=llm.model,
            messages=[
                {"role": "system", "content": "你是产业动态速报编辑。每条摘要必须让读者一眼看出：谁做了什么、发生了什么具体事件。杜绝模糊表述。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=50
        )
        
        summary = response.choices[0].message.content.strip()
        # 清理可能的引号、冒号等符号
        summary = summary.strip('"').strip("'").strip('：').strip(':').strip()
        
        return summary if len(summary) <= 30 else summary[:30]
        
    except Exception as e:
        logger.warning(f"DeepSeek生成摘要失败: {e}")
        # 降级方案：使用标题
        return article_title[:30] + ('...' if len(article_title) > 30 else '')


class MonitorRequest(BaseModel):
    """监控请求模型"""
    entity_id: str
    entity_name: str
    entity_type: str
    priority: str = "normal"  # low, normal, high
    reason: str = "人工添加监控"  # 添加原因


class InvestigateRequest(BaseModel):
    """研判请求模型"""
    entity_id: str
    depth: int = 2  # 关系深度


@router.post("/monitor/add")
async def add_to_monitor(request: MonitorRequest):
    """
    将实体添加到监控列表
    
    Args:
        request: 监控请求，包含实体信息和优先级
        
    Returns:
        操作结果
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 检查是否已存在
        existing = mongodb_conn.find_one(
            'monitored_entities',
            {'entity_id': request.entity_id}
        )
        
        if existing:
            return {
                "success": False,
                "message": f"实体 {request.entity_name} 已在监控列表中"
            }
        
        # 添加到监控列表
        monitor_doc = {
            'entity_id': request.entity_id,
            'entity_name': request.entity_name,
            'entity_type': request.entity_type,
            'priority': request.priority,
            'reason': request.reason,
            'added_at': datetime.now(),
            'status': 'active',
            'alert_count': 0
        }
        
        mongodb_conn.insert_one('monitored_entities', monitor_doc)
        
        logger.info(f"已添加实体到监控列表: {request.entity_name}")
        
        return {
            "success": True,
            "message": f"已将 {request.entity_name} 添加到监控列表",
            "monitor_id": str(monitor_doc.get('_id'))
        }
        
    except Exception as e:
        logger.error(f"添加监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/monitor/remove/{entity_id}")
async def remove_from_monitor(entity_id: str):
    """
    从监控列表移除实体（通过entity_id）
    
    Args:
        entity_id: 实体ID
        
    Returns:
        操作结果
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        result = mongodb_conn.delete_one(
            'monitored_entities',
            {'entity_id': entity_id}
        )
        
        if result.deleted_count > 0:
            logger.info(f"已从监控列表移除实体: {entity_id}")
            return {
                "success": True,
                "message": "已从监控列表移除"
            }
        else:
            return {
                "success": False,
                "message": "实体不在监控列表中"
            }
            
    except Exception as e:
        logger.error(f"移除监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class RemoveMonitorRequest(BaseModel):
    """移除监控请求模型"""
    monitor_id: str


@router.post("/monitor/remove")
async def remove_monitor_by_id(request: RemoveMonitorRequest):
    """
    从监控列表移除实体（通过monitor_id）
    
    Args:
        request: 包含monitor_id的请求
        
    Returns:
        操作结果
    """
    try:
        from app.database.mongodb import mongodb_conn
        from bson import ObjectId
        
        # 通过_id删除
        result = mongodb_conn.delete_one(
            'monitored_entities',
            {'_id': ObjectId(request.monitor_id)}
        )
        
        if result.deleted_count > 0:
            logger.info(f"已从监控列表移除监控项: {request.monitor_id}")
            return {
                "success": True,
                "message": "已从监控列表移除"
            }
        else:
            logger.warning(f"未找到监控项: {request.monitor_id}")
            raise HTTPException(status_code=404, detail="监控项不存在")
            
    except Exception as e:
        logger.error(f"移除监控失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitor/list")
async def get_monitor_list():
    """
    获取监控列表
    
    Returns:
        监控实体列表，包含实时动量数据
    """
    try:
        from app.database.mongodb import mongodb_conn
        from bson import ObjectId
        
        monitors = list(mongodb_conn.find_many(
            'monitored_entities',
            {'status': 'active'},
            sort=[('added_at', -1)]
        ))
        
        # 关联canonical_entities获取完整实体信息
        enriched_monitors = []
        for monitor in monitors:
            # 尝试通过entity_id或_id查找实体
            entity = None
            entity_id = monitor['entity_id']
            
            # 方法1: 直接用entity_id作为_id查找
            entity = mongodb_conn.find_one(
                'canonical_entities',
                {'_id': entity_id}
            )
            
            # 方法2: 如果找不到，尝试在names数组中查找匹配的名称
            if not entity and monitor.get('entity_name'):
                entity = mongodb_conn.find_one(
                    'canonical_entities',
                    {'names': monitor['entity_name']}
                )
            
            if entity:
                # 获取实体的主名称（names数组的第一个）
                entity_name = entity.get('names', [monitor.get('entity_name', '未知')])[0] if entity.get('names') else monitor.get('entity_name', '未知')
                
                # 计算24h动量变化
                momentum_change_24h = 0.0
                if 'momentum_history' in entity and len(entity['momentum_history']) >= 2:
                    history = entity['momentum_history']
                    current = history[-1].get('value', 0)  # 字段是value不是momentum
                    prev = history[-2].get('value', 0)
                    if prev > 0:
                        momentum_change_24h = (current - prev) / prev
                
                # 查找与该实体相关的最新新闻
                latest_news_summary = '监控中'
                try:
                    # 从crawled_articles中查找包含该实体的最新文章
                    entity_type = entity.get('type', 'companies')
                    articles = mongodb_conn.find_many(
                        'crawled_articles',
                        {f'entities.{entity_type}': entity_name, 'processed': True},
                        sort=[('published_at', -1)],
                        limit=1
                    )
                    
                    if articles and len(articles) > 0:
                        latest_article = articles[0]
                        title = latest_article.get('title', '')
                        content = latest_article.get('content', '')
                        
                        # 使用DeepSeek生成智能摘要
                        latest_news_summary = generate_smart_summary(entity_name, title, content)
                        
                    else:
                        # 如果没有找到文章，根据动量变化生成动态描述
                        if abs(momentum_change_24h) > 0.05:
                            if momentum_change_24h > 0:
                                latest_news_summary = f"24h热度上升{abs(momentum_change_24h)*100:.1f}%"
                            else:
                                latest_news_summary = f"24h热度回落{abs(momentum_change_24h)*100:.1f}%"
                        else:
                            latest_news_summary = "动量稳定，持续监控中"
                except Exception as e:
                    logger.warning(f"获取实体 {entity_name} 最新新闻失败: {e}")
                    # 出错时也生成动态描述
                    if abs(momentum_change_24h) > 0.05:
                        latest_news_summary = f"动量变化{momentum_change_24h*100:+.1f}%"
                    else:
                        latest_news_summary = "持续监控中"
                
                enriched_monitor = {
                    'id': str(monitor['_id']),
                    'entity_id': str(entity['_id']),  # 使用实际的_id
                    'entity_name': entity_name,
                    'entity_type': entity.get('type', monitor.get('entity_type', 'unknown')),
                    'priority': monitor.get('priority', 'normal'),
                    'reason': latest_news_summary,
                    'momentum_change_24h': momentum_change_24h,
                    'current_momentum': entity.get('current_momentum', 0),
                    'momentum_history': entity.get('momentum_history', [])[-7:],  # 最近7天
                    'added_at': monitor['added_at'].isoformat() if 'added_at' in monitor else None,
                    'alert_count': monitor.get('alert_count', 0)
                }
                enriched_monitors.append(enriched_monitor)
            else:
                # 实体已被删除，但监控记录还在
                logger.warning(f"监控实体不存在: {monitor['entity_id']}")
        
        # 统计活跃实体（24h变化超过±5%）
        active_threshold = 0.05
        active_entities = [m for m in enriched_monitors if abs(m['momentum_change_24h']) > active_threshold]
        active_count = len(active_entities)
        
        # 获取显著异动的实体（按变化幅度排序，取前3个）
        significant_entities = sorted(active_entities, key=lambda x: abs(x['momentum_change_24h']), reverse=True)[:3]
        significant_names = [e['entity_name'] for e in significant_entities]
        
        return {
            "success": True,
            "count": len(enriched_monitors),
            "monitors": enriched_monitors,
            "summary": {
                "total_count": len(enriched_monitors),
                "active_count": active_count,
                "significant_entities": significant_names
            }
        }
        
    except Exception as e:
        logger.error(f"获取监控列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigate")
async def investigate_entity(request: InvestigateRequest):
    """
    研判溯源 - 分析实体的关联关系和历史动态
    
    Args:
        request: 研判请求，包含实体ID和关系深度
        
    Returns:
        研判结果，包含关联关系、历史趋势等
    """
    try:
        from app.database.mongodb import mongodb_conn
        from app.services.graph_service import graph_service
        from app.analytics.momentum import momentum_engine
        from datetime import timedelta
        from bson import ObjectId
        
        entity_id = request.entity_id
        depth = request.depth
        
        # 1. 获取实体基本信息（从canonical_entities）
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        if not entity:
            raise HTTPException(status_code=404, detail="实体不存在")
        
        # 提取实体名称用于Neo4j查询
        entity_name = entity['names'][0] if entity.get('names') else entity_id
        
        # 2. 从Neo4j获取关联关系（使用实体名称，因为Neo4j中存储的是name）
        logger.info(f"查询实体 {entity_name} 的关联关系...")
        relations = []
        try:
            # 使用Neo4j查询关联关系
            query = f"""
            MATCH (e:Entity {{name: $entity_name}})-[r]-(related:Entity)
            RETURN DISTINCT 
                related.name as related_entity,
                related.type as related_type,
                type(r) as relation_type,
                properties(r) as relation_props
            LIMIT 100
            """
            
            neo4j_results = graph_service.neo4j.execute_query(
                query, 
                {"entity_name": entity_name}
            )
            
            for record in neo4j_results:
                relations.append({
                    "related_entity": record.get('related_entity'),
                    "related_type": record.get('related_type'),
                    "relation_type": record.get('relation_type'),
                    "confidence": record.get('relation_props', {}).get('confidence', 0.9)
                })
            
            logger.info(f"找到 {len(relations)} 个关联关系")
        except Exception as e:
            logger.warning(f"查询Neo4j关联关系失败: {e}")
            relations = []
        
        # 3. 获取历史动量趋势（最近30天）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        momentum_trend = momentum_engine.get_momentum_trend(
            entity_id,
            start_time,
            end_time,
            interval_days=1
        )
        
        # 4. 获取所有相关文档（直接从crawled_articles查询）
        # 通过实体名称在文章标题或内容中搜索
        logger.info(f"从crawled_articles查询包含 {entity_name} 的文章...")
        
        documents = []
        try:
            # 使用正则表达式搜索标题或内容中包含实体名称的文章
            articles = list(mongodb_conn.get_collection('crawled_articles').find(
                {
                    '$or': [
                        {'title': {'$regex': entity_name, '$options': 'i'}},
                        {'content': {'$regex': entity_name, '$options': 'i'}}
                    ]
                },
                {
                    '_id': 1,
                    'title': 1,
                    'content': 1,
                    'url': 1,
                    'source': 1,
                    'crawled_at': 1
                }
            ).sort('crawled_at', -1))
            
            logger.info(f"从crawled_articles找到 {len(articles)} 篇相关文章")
            
            for article in articles:
                documents.append({
                    '_id': str(article['_id']),
                    'title': article.get('title', '无标题'),
                    'content': article.get('content', '')[:200],  # 只保留前200字符
                    'source_url': article.get('url', ''),
                    'source': article.get('source', ''),
                    'created_at': article['crawled_at'].isoformat() if 'crawled_at' in article else '',
                    'sentiment': {}
                })
        except Exception as e:
            logger.error(f"从crawled_articles查询文章失败: {e}", exc_info=True)
        
        logger.info(f"最终返回 {len(documents)} 条文档数据")
        
        return {
            "success": True,
            "entity": {
                "id": entity['_id'],
                "name": entity_name,
                "type": entity.get('type'),
                "current_momentum": entity.get('current_momentum', 0),  # 直接使用数据库中的值
                "reference_count": entity.get('reference_count', 0)
            },
            "relations": relations,
            "momentum_trend": momentum_trend,
            "recent_documents": documents,
            "analysis": {
                "total_relations": len(relations) if relations else 0,
                "total_documents": len(documents),
                "momentum_direction": "上升" if len(momentum_trend) >= 2 and momentum_trend[-1]['value'] > momentum_trend[0]['value'] else "下降"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"研判溯源失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-report")
async def generate_ai_report(entity_id: str = Body(..., embed=True)):
    """
    生成实体的AI简报（整合实体信息、关系网络、新闻内容、动量趋势）
    
    Args:
        entity_id: 实体ID
        
    Returns:
        AI生成的简报内容
    """
    try:
        from app.database.mongodb import mongodb_conn
        from app.nlp.llm import llm_processor
        from app.services.graph_service import graph_service
        from app.analytics.momentum import momentum_engine
        from datetime import timedelta
        
        # 1. 获取实体基本信息
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        if not entity:
            raise HTTPException(status_code=404, detail="实体不存在")
        
        entity_name = entity['names'][0] if entity.get('names') else '未知实体'
        
        # 2. 获取Neo4j关系数据
        relations_summary = ""
        try:
            query = """
            MATCH (e:Entity {name: $entity_name})-[r]-(related:Entity)
            RETURN DISTINCT 
                related.name as related_entity,
                related.type as related_type,
                type(r) as relation_type
            LIMIT 20
            """
            neo4j_results = graph_service.neo4j.execute_query(query, {"entity_name": entity_name})
            
            if neo4j_results:
                relations_by_type = {}
                for record in neo4j_results:
                    rel_type = record.get('relation_type', '未知关系')
                    if rel_type not in relations_by_type:
                        relations_by_type[rel_type] = []
                    relations_by_type[rel_type].append(record.get('related_entity', ''))
                
                relations_summary = "\n".join([
                    f"- {rel_type}: {', '.join(entities[:5])}" + (f" 等{len(entities)}个" if len(entities) > 5 else "")
                    for rel_type, entities in relations_by_type.items()
                ])
            else:
                relations_summary = "- 暂无关联关系数据"
        except Exception as e:
            logger.warning(f"获取关系数据失败: {e}")
            relations_summary = "- 关系数据暂不可用"
        
        # 3. 获取真实新闻文章（从crawled_articles，包含完整内容）
        crawled_articles = mongodb_conn.get_collection('crawled_articles')
        articles = list(crawled_articles.find({
            '$or': [
                {'title': {'$regex': entity_name, '$options': 'i'}},
                {'content': {'$regex': entity_name, '$options': 'i'}}
            ]
        }).sort('publish_date', -1).limit(15))
        
        logger.info(f"为{entity_name}找到{len(articles)}篇相关文章")
        
        # 构建新闻摘要（包含标题、日期、关键内容）
        news_details = []
        for i, article in enumerate(articles[:10], 1):
            title = article.get('title', '无标题')
            pub_date = article.get('publish_date', '').strftime('%Y-%m-%d') if article.get('publish_date') else '日期未知'
            content = article.get('content', '')[:200] + '...' if article.get('content') else '无内容'
            news_details.append(f"{i}. 【{pub_date}】{title}\n   {content}")
        
        news_summary = "\n\n".join(news_details) if news_details else "暂无相关新闻"
        
        logger.info(f"新闻摘要长度: {len(news_summary)} 字符")
        
        # 4. 获取历史动量趋势（直接从MongoDB查询）
        momentum_trend_desc = ""
        try:
            momentum_history_collection = mongodb_conn.get_collection('momentum_history')
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            momentum_history = list(momentum_history_collection.find({
                'entity_id': entity_id,
                'date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }).sort('date', 1))
            
            if momentum_history and len(momentum_history) > 1:
                first_momentum = momentum_history[0].get('value', 0)
                last_momentum = momentum_history[-1].get('value', 0)
                change = ((last_momentum - first_momentum) / first_momentum * 100) if first_momentum > 0 else 0
                momentum_trend_desc = f"30天内动量变化: {change:+.1f}%（{first_momentum*100:.1f}% → {last_momentum*100:.1f}%）"
            else:
                momentum_trend_desc = "暂无历史动量数据"
        except Exception as e:
            logger.warning(f"获取历史动量失败: {e}")
            momentum_trend_desc = "暂无历史动量数据"
        
        # 5. 计算动量趋势
        momentum_change = entity.get('momentum_change', 0)
        momentum_trend = "上升" if momentum_change > 0 else "下降" if momentum_change < 0 else "平稳"
        momentum_pct = (entity.get('current_momentum', 0) * 100)
        
        # 6. 构建综合提示词
        logger.info(f"开始构建prompt，关联关系: {len(neo4j_results) if neo4j_results else 0}, 文章数: {len(articles)}")
        
        prompt = f"""你是一位专业的产业分析师。请基于以下真实数据，为"{entity_name}"生成一份深度AI简报。

# 数据总览

## 实体基本信息
- **名称**: {entity_name}
- **类型**: {entity.get('type', '未知')}
- **当前热度**: {momentum_pct:.1f}%
- **短期趋势**: {momentum_trend} ({momentum_change:+.2%})
- **引用次数**: {entity.get('reference_count', 0)}次
- **{momentum_trend_desc}**

## 关联实体网络（共{len(neo4j_results) if 'neo4j_results' in locals() else 0}个）
{relations_summary}

## 最近新闻报道（共{len(articles)}条）
{news_summary}

---

# 简报要求

请严格按照以下结构生成专业简报：

## 📋 实体概览
基于实体类型和关联网络，3-5句话概述其行业定位和核心价值。

## 📈 近期动态
详细分析最近的新闻报道，引用具体标题和日期，提炼关键事件、技术突破、市场动向。

## 🔥 热度趋势研判
分析{momentum_pct:.1f}%热度的成因，结合新闻事件解读{momentum_trend}趋势背后的产业逻辑，预测未来1-2周趋势。

## 🔗 关联生态分析
基于关系网络分析产业链上下游，识别关键合作伙伴或竞争对手。

## 💡 投资/关注建议
综合热度、趋势、新闻给出明确建议，标注风险点和机会点。

**重要格式要求**:
1. 直接开始正文，不要任何开场白或"好的，这是..."等客套话
2. 使用Markdown格式，包含emoji、加粗、列表、代码块
3. 引用具体数据和新闻标题
4. 标题不要加字数说明（如"实体概览"而非"实体概览（120字）"）
5. 总长度800-1000字
6. 专业、客观、可操作
"""

        # 调用LLM生成简报
        report = llm_processor.generate_text(prompt, max_tokens=2000)
        
        # 保存简报记录
        report_doc = {
            'entity_id': entity_id,
            'entity_name': entity_name,
            'report_content': report,
            'generated_at': datetime.now(),
            'document_count': len(articles),
            'relations_count': len(neo4j_results) if neo4j_results else 0
        }
        mongodb_conn.insert_one('ai_reports', report_doc)
        
        logger.info(f"已生成AI简报: {entity_name}，包含{len(articles)}篇文章，{len(neo4j_results) if neo4j_results else 0}个关联关系")
        
        return {
            "success": True,
            "entity_name": entity_name,
            "report": report,
            "document_count": len(articles),
            "relations_count": len(neo4j_results) if neo4j_results else 0,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成AI简报失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-data")
async def export_entity_data(entity_id: str = Body(..., embed=True)):
    """
    导出实体的原始数据
    
    Args:
        entity_id: 实体ID
        
    Returns:
        实体的完整数据（JSON格式）
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 获取实体信息
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        if not entity:
            raise HTTPException(status_code=404, detail="实体不存在")
        
        # 获取所有相关文档
        documents = list(mongodb_conn.find_many(
            'document_instances',
            {'entity_references.entity_id': entity_id},
            sort=[('created_at', -1)]
        ))
        
        # 转换格式
        entity['_id'] = str(entity['_id'])
        if 'last_updated' in entity:
            entity['last_updated'] = entity['last_updated'].isoformat()
        
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            if 'created_at' in doc:
                doc['created_at'] = doc['created_at'].isoformat()
        
        export_data = {
            "entity": entity,
            "documents": documents,
            "export_time": datetime.now().isoformat(),
            "total_documents": len(documents)
        }
        
        logger.info(f"已导出实体数据: {entity.get('names', ['未知'])[0]}")
        
        return {
            "success": True,
            "data": export_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hide-entity")
async def hide_entity(entity_id: str = Body(..., embed=True)):
    """
    屏蔽实体（将其添加到黑名单）
    
    Args:
        entity_id: 实体ID
        
    Returns:
        操作结果
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 获取实体信息
        entity = mongodb_conn.find_one('canonical_entities', {'_id': entity_id})
        if not entity:
            raise HTTPException(status_code=404, detail="实体不存在")
        
        # 添加到黑名单
        blacklist_doc = {
            'entity_id': entity_id,
            'entity_name': entity['names'][0] if entity.get('names') else '未知',
            'entity_type': entity.get('type'),
            'hidden_at': datetime.now(),
            'reason': 'user_hidden',
            'status': 'active'
        }
        
        mongodb_conn.insert_one('entity_blacklist', blacklist_doc)
        
        # 更新实体状态
        mongodb_conn.update_one(
            'canonical_entities',
            {'_id': entity_id},
            {'$set': {'hidden': True, 'hidden_at': datetime.now()}}
        )
        
        logger.info("✅ 实体hidden状态已更新")
        
        # 清除动量排行榜的Redis缓存
        logger.info("开始导入redis_conn...")
        from app.database.redis_db import redis_conn
        logger.info(f"准备清除缓存，redis_conn._client: {redis_conn._client}")
        # 清除所有动量排行榜缓存（因为不知道用户用了哪些参数）
        cache_pattern = "momentum:top:*"
        keys = redis_conn._client.keys(cache_pattern)
        logger.info(f"找到缓存keys: {keys}")
        if keys:
            deleted_count = redis_conn._client.delete(*keys)
            logger.info(f"✅ 已清除 {deleted_count} 个动量排行榜缓存")
        else:
            logger.info("没有找到需要清除的缓存keys")
        
        logger.info(f"已屏蔽实体: {entity.get('names', ['未知'])[0]}")
        
        return {
            "success": True,
            "message": f"已屏蔽实体: {entity.get('names', ['未知'])[0]}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"屏蔽实体失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
