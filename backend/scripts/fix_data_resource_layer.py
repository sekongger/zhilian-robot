"""修复数据资源层：补充数据源管理集合数据"""

import sys
import os
from datetime import datetime, timezone
from bson import ObjectId

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.mongodb import mongodb_conn


def fix_data_resource_layer():
    """补充数据资源层的数据源管理集合"""
    
    print("=" * 60)
    print("修复数据资源层 - 补充数据源管理集合")
    print("=" * 60)
    
    # 1. 创建默认数据源基础信息
    ds_basic_info = mongodb_conn.get_collection("ds_basic_info")
    
    default_sources = [
        {
            "ds_id": "DS_CRAWLER_001",
            "name": "历史爬虫数据源",
            "description": "从crawled_articles迁移的历史数据",
            "credibility_score": 85.0,
            "metadata": {"language": "中文", "coverage_area": "全国", "update_cycle": "实时"},
            "ds_type": "INTERNET",
            "data_category": "资讯",
            "ds_source": "crawler_system",
            "responsible_person": "系统管理员",
            "create_time": datetime.now(timezone.utc),
            "update_time": datetime.now(timezone.utc),
            "is_valid": True
        },
        {
            "ds_id": "DS_MANUAL_001",
            "name": "手动录入数据源",
            "description": "通过前端手动录入的资讯数据",
            "credibility_score": 90.0,
            "metadata": {"language": "中文", "coverage_area": "全国", "update_cycle": "按需"},
            "ds_type": "FILL",
            "data_category": "资讯",
            "ds_source": "manual_input",
            "responsible_person": "系统管理员",
            "create_time": datetime.now(timezone.utc),
            "update_time": datetime.now(timezone.utc),
            "is_valid": True
        },
        {
            "ds_id": "DS_API_2026_001",
            "name": "产业政策API数据源",
            "description": "产业政策官网API接入",
            "credibility_score": 95.0,
            "metadata": {"language": "中文", "coverage_area": "全国", "update_cycle": "日度"},
            "ds_type": "API",
            "data_category": "产业政策",
            "ds_source": "https://policy.example.gov.cn",
            "responsible_person": "系统管理员",
            "create_time": datetime.now(timezone.utc),
            "update_time": datetime.now(timezone.utc),
            "is_valid": True
        }
    ]
    
    for source in default_sources:
        existing = ds_basic_info.find_one({"ds_id": source["ds_id"]})
        if not existing:
            ds_basic_info.insert_one(source)
            print(f"✓ 创建数据源: {source['ds_id']} - {source['name']}")
        else:
            print(f"- 数据源已存在: {source['ds_id']}")
    
    # 2. 创建默认接入任务
    ds_access_task = mongodb_conn.get_collection("ds_access_task")
    
    default_tasks = [
        {
            "task_id": "TASK_DS_CRAWLER_001_0001",
            "ds_id": "DS_CRAWLER_001",
            "task_name": "历史数据迁移任务",
            "access_mode": "FULL",
            "priority": 1,
            "schedule_config": "manual",
            "access_params": {},
            "storage_config": {"storage_type": "MONGO", "storage_addr": "news_pipeline_source_news"},
            "remark": "一次性迁移历史crawled_articles数据",
            "is_valid": True,
            "create_time": datetime.now(timezone.utc),
            "update_time": datetime.now(timezone.utc)
        },
        {
            "task_id": "TASK_DS_MANUAL_001_0001",
            "ds_id": "DS_MANUAL_001",
            "task_name": "手动录入任务",
            "access_mode": "REAL_TIME",
            "priority": 1,
            "schedule_config": "on_demand",
            "access_params": {},
            "storage_config": {"storage_type": "MONGO", "storage_addr": "news_pipeline_source_news"},
            "remark": "前端手动录入资讯",
            "is_valid": True,
            "create_time": datetime.now(timezone.utc),
            "update_time": datetime.now(timezone.utc)
        }
    ]
    
    for task in default_tasks:
        existing = ds_access_task.find_one({"task_id": task["task_id"]})
        if not existing:
            ds_access_task.insert_one(task)
            print(f"✓ 创建接入任务: {task['task_id']} - {task['task_name']}")
        else:
            print(f"- 接入任务已存在: {task['task_id']}")
    
    # 3. 为已有的source_news补充数据源字段
    source_news = mongodb_conn.get_collection("news_pipeline_source_news")
    
    # 统计需要更新的记录
    need_update = source_news.count_documents({
        "$or": [
            {"ds_id": {"$exists": False}},
            {"task_id": {"$exists": False}},
            {"task_runtime_id": {"$exists": False}}
        ]
    })
    
    if need_update > 0:
        print(f"\n发现 {need_update} 条记录缺少数据源字段，开始补充...")
        
        # 批量更新
        result = source_news.update_many(
            {"ds_id": {"$exists": False}},
            {"$set": {
                "ds_id": "DS_CRAWLER_001",
                "task_id": "TASK_DS_CRAWLER_001_0001",
                "task_runtime_id": f"RECORD_TASK_DS_CRAWLER_001_0001_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }}
        )
        print(f"✓ 更新了 {result.modified_count} 条记录的数据源字段")
        
        # 创建对应的执行记录
        ds_access_record = mongodb_conn.get_collection("ds_access_record")
        
        record = {
            "record_id": f"RECORD_TASK_DS_CRAWLER_001_0001_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "task_id": "TASK_DS_CRAWLER_001_0001",
            "ds_id": "DS_CRAWLER_001",
            "exec_status": "SUCCESS",
            "total_count": result.modified_count,
            "valid_count": result.modified_count,
            "invalid_count": 0,
            "start_time": datetime.now(timezone.utc),
            "end_time": datetime.now(timezone.utc),
            "exec_time": 0,
            "error_msg": ""
        }
        ds_access_record.insert_one(record)
        print(f"✓ 创建执行记录: {record['record_id']}")
    
    # 4. 为raw_documents补充数据源字段
    raw_documents = mongodb_conn.get_collection("raw_documents")
    raw_need_update = raw_documents.count_documents({"ds_id": {"$exists": False}})
    
    if raw_need_update > 0:
        print(f"\n发现 {raw_need_update} 条raw_documents缺少数据源字段，开始补充...")
        result = raw_documents.update_many(
            {"ds_id": {"$exists": False}},
            {"$set": {
                "ds_id": "DS_CRAWLER_001",
                "task_id": "TASK_DS_CRAWLER_001_0001",
                "task_runtime_id": f"RECORD_TASK_DS_CRAWLER_001_0001_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }}
        )
        print(f"✓ 更新了 {result.modified_count} 条raw_documents的数据源字段")
    
    print("\n" + "=" * 60)
    print("数据资源层修复完成！")
    print("=" * 60)
    
    # 打印统计
    print("\n当前统计：")
    print(f"- 数据源基础信息: {ds_basic_info.count_documents({})}")
    print(f"- 接入任务: {ds_access_task.count_documents({})}")
    print(f"- 执行记录: {mongodb_conn.get_collection('ds_access_record').count_documents({})}")
    print(f"- 原始文档: {raw_documents.count_documents({})}")
    print(f"- 贴源明细: {source_news.count_documents({})}")


if __name__ == "__main__":
    fix_data_resource_layer()
