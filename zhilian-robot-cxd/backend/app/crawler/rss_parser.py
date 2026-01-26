"""
RSS订阅解析器 - 订阅行业动态
"""
import feedparser
import logging
from typing import List, Dict
from datetime import datetime
from time import mktime

logger = logging.getLogger(__name__)


class RSSFeedParser:
    """RSS订阅解析器"""
    
    def __init__(self):
        # 预定义的RSS源 - 聚焦机器人和自动化行业
        # 注意:部分行业垂直RSS源存在格式问题,优先使用通用科技源并手动筛选机器人相关内容
        self.feeds = {
            # 通用科技新闻(包含大量机器人/AI内容)
            'ithome': 'https://www.ithome.com/rss/',  # IT之家
            '36kr': 'https://36kr.com/feed',  # 36氪(创投/科技)
            'cnbeta': 'https://www.cnbeta.com.tw/backend.php',  # CNBeta
            
            # AI和机器学习
            # 'jiqizhixin': 'https://www.jiqizhixin.com/rss',  # 机器之心(XML错误)
            
            # 科技媒体
            'ifanr': 'https://www.ifanr.com/feed',  # 爱范儿
            #有问题'geekpark': 'http://www.geekpark.net/rss',  # 极客公园
            
            # === 新增专业源 ===
            # 机器之心 (AI与机器人) - 建议使用 RSSHub 等工具转换的标准链接，或尝试直接解析
            #有问题'jiqizhixin': 'https://www.jiqizhixin.com/rss',
            
            # 雷锋网 (智能驾驶与机器人)
            'leiphone': 'https://www.leiphone.com/feed',
            
            # 智东西 (硬科技)
            #有问题'zhidx': 'https://zhidx.com/feed',
            
            # IEEE Spectrum 机器人 (国际权威，需确保网络可达)
            #有问题'ieee_robotics': 'https://spectrum.ieee.org/feeds/topic/robotics',
            
            # 麻省理工科技评论 (新兴技术)
            'mit_tech': 'https://www.technologyreview.com/feed/',

            # 备注:专业机器人/工控类RSS源多数存在XML格式问题
            # 已测试但无法使用的源:
            # - robot_china: XML entity错误
            # - gongkong: 编码问题
            # - ofweek_robot: XML tag错误
            # - leiphone_robot: XML tag错误
            # 建议:使用通用科技源+关键词过滤来获取机器人相关内容
        }
    
    def parse_feed(self, feed_url_or_name: str, max_entries: int = 10) -> List[Dict]:
        """
        解析单个RSS源
        
        Args:
            feed_url_or_name: RSS源URL或预定义名称
            max_entries: 最大条目数
            
        Returns:
            文章列表
        """
        # 如果是预定义名称,获取URL
        if feed_url_or_name in self.feeds:
            feed_url = self.feeds[feed_url_or_name]
            feed_name = feed_url_or_name
        else:
            feed_url = feed_url_or_name
            feed_name = feed_url.split('//')[1].split('/')[0] if '//' in feed_url else 'unknown'
        
        try:
            logger.info(f"正在解析RSS源: {feed_name} ({feed_url})")
            
            # feedparser可以直接处理URL,并自动设置User-Agent
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"RSS源可能存在问题: {feed_name}, 错误: {feed.get('bozo_exception', 'Unknown')}")
            
            if not feed.entries:
                logger.warning(f"RSS源无条目: {feed_name}")
                return []
            
            results = []
            for entry in feed.entries[:max_entries]:
                try:
                    # 提取发布时间
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published = datetime.fromtimestamp(mktime(entry.published_parsed))
                        except:
                            pass
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        try:
                            published = datetime.fromtimestamp(mktime(entry.updated_parsed))
                        except:
                            pass
                    
                    # 提取内容
                    content = ''
                    if hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    elif hasattr(entry, 'content'):
                        content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                    
                    # 清理HTML标签
                    from bs4 import BeautifulSoup
                    content_text = BeautifulSoup(content, 'html.parser').get_text(strip=True)
                    
                    # 至少要有一些内容
                    if len(content_text) < 30:
                        logger.debug(f"跳过内容过短的条目: {entry.get('title', 'No title')[:30]}")
                        continue
                    
                    # 提取标题
                    title = entry.title if hasattr(entry, 'title') else 'No Title'
                    
                    # 提取链接
                    link = ''
                    if hasattr(entry, 'link'):
                        link = entry.link
                    elif hasattr(entry, 'links') and entry.links:
                        link = entry.links[0].get('href', '')
                    
                    results.append({
                        'title': title,
                        'content': content_text[:2000],  # 限制内容长度
                        'source': f'rss_{feed_name}',
                        'url': link,
                        'published_at': published,
                        'crawled_at': datetime.now()
                    })
                    
                except Exception as e:
                    logger.warning(f"解析RSS条目失败: {e}")
                    continue
            
            logger.info(f"RSS源 {feed_name} 解析完成: {len(results)}/{len(feed.entries)} 条")
            return results
            
        except Exception as e:
            logger.error(f"解析RSS源失败 {feed_name}: {e}", exc_info=True)
            return []
    
    def parse_all_feeds(self, max_entries_per_feed: int = 5, hours_ago: int = 24) -> List[Dict]:
        """
        解析所有预定义的RSS源
        
        Args:
            max_entries_per_feed: 每个源的最大条目数
            hours_ago: 只获取最近N小时的文章（默认24小时）
            
        Returns:
            所有文章列表
        """
        from datetime import timedelta
        
        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=hours_ago)
        
        for feed_name, feed_url in self.feeds.items():
            logger.info(f"正在处理RSS源: {feed_name}")
            try:
                articles = self.parse_feed(feed_name, max_entries=max_entries_per_feed)
                
                # 过滤出最近N小时的文章
                recent_articles = [
                    article for article in articles 
                    if article.get('published_at', datetime.min) >= cutoff_time
                ]
                
                all_articles.extend(recent_articles)
                
                if len(recent_articles) < len(articles):
                    logger.info(f"✅ {feed_name}: 获取 {len(recent_articles)} 条 (过滤掉 {len(articles) - len(recent_articles)} 条旧文章)")
                else:
                    logger.info(f"✅ {feed_name}: 获取 {len(articles)} 条")
            except Exception as e:
                logger.error(f"❌ {feed_name} 处理失败: {e}")
                continue
        
        logger.info(f"RSS订阅总共获取: {len(all_articles)} 条文章 (最近{hours_ago}小时)")
        return all_articles
    
    def add_feed(self, name: str, url: str):
        """添加新的RSS源"""
        self.feeds[name] = url
        logger.info(f"添加RSS源: {name} -> {url}")
    
    def remove_feed(self, name: str):
        """移除RSS源"""
        if name in self.feeds:
            del self.feeds[name]
            logger.info(f"移除RSS源: {name}")


# 全局RSS解析器实例
rss_parser = RSSFeedParser()
