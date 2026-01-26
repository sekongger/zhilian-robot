#!/usr/bin/env python3
"""
回溯计算历史动量数据

⚠️ 重要提示：
- 此脚本依赖历史文档实例数据（document_instances）
- 如果过去的日期没有文档实例，计算的动量值将为0
- 建议在系统运行一段时间后（有足够历史数据）再使用

📋 使用场景：
1. 数据库迁移后重建历史数据
2. 调整动量计算逻辑后重新计算历史动量
3. 为新导入的实体补充历史动量记录
4. 修复历史数据不一致问题

💡 使用方法：
    # 回填最近7天的历史动量
    docker exec zhilian-backend python /app/scripts/backfill_momentum_history.py --days 7
    
    # 回填最近30天的历史动量
    docker exec zhilian-backend python /app/scripts/backfill_momentum_history.py --days 30

⚠️ 注意事项：
- 此操作会清空现有的 momentum_history 数组
- 处理时间较长（971个实体 × 30天 ≈ 3-5分钟）
- 建议在低峰期执行
- 执行前建议备份数据库

📊 数据要求：
- 需要有足够的历史文档实例数据
- 文档实例的 created_at 需要分布在不同日期
- 如果所有文档都是同一天创建的，历史动量将都相同
"""
import sys
sys.path.insert(0, '/app')

from app.database.mongodb import mongodb_conn, canonical_entity_manager
from app.analytics.momentum import momentum_engine
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backfill_momentum_history(days=30):
    """
    回溯填充历史动量数据
    
    Args:
        days: 回溯天数
    """
    try:
        if not mongodb_conn._db:
            mongodb_conn.connect()
        
        # 获取所有实体
        entities = list(mongodb_conn._db.canonical_entities.find({}, {'_id': 1}))
        logger.info(f"找到 {len(entities)} 个实体")
        
        # 清空现有的历史记录
        logger.info("清空现有历史记录...")
        mongodb_conn._db.canonical_entities.update_many(
            {},
            {'$set': {'momentum_history': []}}
        )
        
        # 为每一天计算动量
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        current_date = start_date
        day_count = 0
        
        while current_date <= end_date:
            day_count += 1
            logger.info(f"处理第 {day_count}/{days+1} 天: {current_date.strftime('%Y-%m-%d')}")
            
            entity_count = 0
            for entity in entities:
                entity_id = entity['_id']
                
                # 计算该日期的动量
                momentum_value = momentum_engine.calculate_momentum(entity_id, current_date)
                
                # 添加到历史记录
                mongodb_conn._db.canonical_entities.update_one(
                    {'_id': entity_id},
                    {
                        '$push': {
                            'momentum_history': {
                                'date': current_date,
                                'value': momentum_value
                            }
                        }
                    }
                )
                
                entity_count += 1
            
            logger.info(f"  ✅ 完成 {entity_count} 个实体")
            current_date += timedelta(days=1)
        
        logger.info(f"🎉 历史动量回填完成！处理了 {days+1} 天，{len(entities)} 个实体")
        
        # 验证结果
        sample = mongodb_conn._db.canonical_entities.find_one({}, {'_id': 1, 'momentum_history': 1})
        if sample:
            history_count = len(sample.get('momentum_history', []))
            logger.info(f"验证: 实体 {sample['_id']} 有 {history_count} 条历史记录")
        
        return {
            'success': True,
            'days_processed': days + 1,
            'entities_processed': len(entities)
        }
        
    except Exception as e:
        logger.error(f"回填失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='回溯计算历史动量数据')
    parser.add_argument('--days', type=int, default=30, help='回溯天数（默认30天）')
    args = parser.parse_args()
    
    logger.info(f"开始回溯计算最近 {args.days} 天的动量数据...")
    result = backfill_momentum_history(args.days)
    
    if result['success']:
        logger.info("✅ 成功！")
        sys.exit(0)
    else:
        logger.error(f"❌ 失败: {result.get('error')}")
        sys.exit(1)
