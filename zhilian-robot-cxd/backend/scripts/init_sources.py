#!/usr/bin/env python3
"""
数据源初始化脚本
用于预填充权威数据源到MongoDB，为动量计算提供可信度基准
"""
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.database.mongodb import SourceManager
import asyncio

# 权威数据源配置（根据Recorded Future理念设置可信度分数）
AUTHORITATIVE_SOURCES = [
    {
        "name": "财新网",
        "url": "https://www.caixin.com",
        "credibility_score": 0.9,
        "category": "financial_news",
        "description": "中国领先的财经媒体，以深度报道和数据新闻著称",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "36氪",
        "url": "https://36kr.com",
        "credibility_score": 0.8,
        "category": "tech_startup",
        "description": "专注科技创业领域的权威媒体",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "微博",
        "url": "https://weibo.com",
        "credibility_score": 0.3,
        "category": "social_media",
        "description": "中国主流社交媒体平台（可信度较低，需交叉验证）",
        "language": "zh-CN",
        "verified": False
    },
    {
        "name": "新华社",
        "url": "http://www.xinhuanet.com",
        "credibility_score": 0.95,
        "category": "government_news",
        "description": "中国国家通讯社，官方权威信息源",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "人民日报",
        "url": "http://www.people.com.cn",
        "credibility_score": 0.95,
        "category": "government_news",
        "description": "中国共产党中央委员会机关报",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "虎嗅网",
        "url": "https://www.huxiu.com",
        "credibility_score": 0.75,
        "category": "tech_business",
        "description": "科技商业媒体，侧重深度分析",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "知乎",
        "url": "https://www.zhihu.com",
        "credibility_score": 0.4,
        "category": "q_and_a",
        "description": "问答社区，内容质量参差不齐",
        "language": "zh-CN",
        "verified": False
    },
    {
        "name": "界面新闻",
        "url": "https://www.jiemian.com",
        "credibility_score": 0.85,
        "category": "general_news",
        "description": "专业财经新闻平台",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "第一财经",
        "url": "https://www.yicai.com",
        "credibility_score": 0.88,
        "category": "financial_news",
        "description": "上海第一财经传媒有限公司旗下媒体",
        "language": "zh-CN",
        "verified": True
    },
    {
        "name": "澎湃新闻",
        "url": "https://www.thepaper.cn",
        "credibility_score": 0.82,
        "category": "general_news",
        "description": "专业新闻平台，时政与民生并重",
        "language": "zh-CN",
        "verified": True
    }
]

async def init_sources():
    """初始化数据源"""
    source_mgr = SourceManager()
    
    print("=" * 60)
    print("开始初始化权威数据源")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for source_data in AUTHORITATIVE_SOURCES:
        try:
            # 检查是否已存在
            existing = await source_mgr.sources_collection.find_one({
                "name": source_data["name"]
            })
            
            if existing:
                # 更新现有数据源
                await source_mgr.sources_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": source_data}
                )
                print(f"✓ 更新数据源: {source_data['name']} (可信度: {source_data['credibility_score']})")
            else:
                # 注册新数据源
                source_id = await source_mgr.register_source(
                    name=source_data["name"],
                    url=source_data["url"],
                    credibility_score=source_data["credibility_score"],
                    category=source_data.get("category"),
                    metadata={
                        "description": source_data.get("description"),
                        "language": source_data.get("language"),
                        "verified": source_data.get("verified", False)
                    }
                )
                print(f"✓ 新增数据源: {source_data['name']} (可信度: {source_data['credibility_score']})")
            
            success_count += 1
            
        except Exception as e:
            print(f"✗ 处理失败 {source_data['name']}: {str(e)}")
            error_count += 1
    
    print("=" * 60)
    print(f"初始化完成!")
    print(f"成功: {success_count} 个数据源")
    print(f"失败: {error_count} 个数据源")
    print("=" * 60)
    
    # 显示统计信息
    print("\n数据源可信度分布:")
    print("-" * 60)
    high_credibility = [s for s in AUTHORITATIVE_SOURCES if s["credibility_score"] >= 0.8]
    medium_credibility = [s for s in AUTHORITATIVE_SOURCES if 0.5 <= s["credibility_score"] < 0.8]
    low_credibility = [s for s in AUTHORITATIVE_SOURCES if s["credibility_score"] < 0.5]
    
    print(f"  高可信度 (≥0.8): {len(high_credibility)} 个")
    for s in high_credibility:
        print(f"    - {s['name']}: {s['credibility_score']}")
    
    print(f"\n  中可信度 (0.5-0.8): {len(medium_credibility)} 个")
    for s in medium_credibility:
        print(f"    - {s['name']}: {s['credibility_score']}")
    
    print(f"\n  低可信度 (<0.5): {len(low_credibility)} 个")
    for s in low_credibility:
        print(f"    - {s['name']}: {s['credibility_score']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║        智链机器人 - 数据源初始化工具                      ║
║   基于 Recorded Future 时间智能理念                        ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(init_sources())
    
    print("\n提示: 数据源可信度将直接影响实体的动量计算")
    print("建议定期审核和更新数据源的可信度评分")
