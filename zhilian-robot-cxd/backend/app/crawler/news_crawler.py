"""
新闻爬虫 - 爬取产业新闻 (修复版)
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class IndustryNewsCrawler:
    """产业新闻爬虫"""
    
    def __init__(self):
        # 核心修复：使用真实的浏览器 User-Agent，防止被百度/OFweek 直接拦截
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _crawl_baidu_search(self, query: str, source_label: str, max_results: int) -> List[Dict]:
        """通用百度资讯搜索解析器"""
        try:
            logger.info(f"开始百度搜索 [{source_label}]: {query}")
            # 使用百度资讯搜索
            url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={quote(query)}"
            
            # 必须带 Header，否则百度直接返回空或验证码
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"百度搜索返回状态码: {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 百度资讯的新版容器类名通常是 .result-op 或 .c-container
            items = soup.select('.result-op, .c-container')
            
            for item in items[:max_results]:
                try:
                    # 提取标题
                    title_tag = item.select_one('h3 a')
                    if not title_tag: continue
                    
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    # 提取摘要 (尝试多种选择器)
                    content_tag = item.select_one('.c-font-normal-three') 
                    if not content_tag:
                         content_tag = item.select_one('.c-span-last')
                    
                    content = content_tag.get_text(strip=True) if content_tag else title
                    
                    if not title or len(content) < 10: continue
                    
                    results.append({
                        'title': title,
                        'content': content,
                        'source': source_label,
                        'keyword': query,
                        'url': link,
                        'crawled_at': datetime.now()
                    })
                except Exception:
                    continue
            
            logger.info(f"[{source_label}] 爬取完成: {len(results)} 条")
            return results
            
        except Exception as e:
            logger.error(f"[{source_label}] 爬取失败: {e}")
            return []

    def crawl_sina_finance(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        修复版：爬取新浪新闻 (改为网页解析，API已失效)
        """
        try:
            logger.info(f"开始爬取新浪新闻: {keyword}")
            # 使用新浪全网搜索
            url = f"https://search.sina.com.cn/news?q={quote(keyword)}&c=news&size=10&page=1"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            # 新浪搜索结果有时是 GBK，有时是 UTF-8，自动推断
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 结果容器
            items = soup.select('.box-result .r-info')
            
            for item in items[:max_results]:
                try:
                    title_tag = item.select_one('h2 a')
                    if not title_tag: continue
                    
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    content_tag = item.select_one('.content')
                    content = content_tag.get_text(strip=True) if content_tag else title
                    
                    results.append({
                        'title': title,
                        'content': content,
                        'source': 'crawler_sina',
                        'keyword': keyword,
                        'url': link,
                        'crawled_at': datetime.now()
                    })
                except Exception:
                    continue
            
            logger.info(f"新浪新闻爬取完成: {len(results)} 条")
            return results
        except Exception as e:
            logger.error(f"爬取新浪失败: {e}")
            return []
    
    def crawl_36kr(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        修复版：爬取36氪
        (原API已加密，改为利用百度搜索 'site:36kr.com 关键词')
        """
        query = f"site:36kr.com {keyword}"
        return self._crawl_baidu_search(query, 'crawler_36kr', max_results)
    
    def crawl_robot_news(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        修复版：爬取机器人网
        (直接搜关键词，数据源归类为百度新闻)
        """
        return self._crawl_baidu_search(keyword, 'crawler_baidu', max_results)
    
    def crawl_ofweek_robot(self, keyword: str, max_results: int = 10) -> List[Dict]:
        """
        修复版：爬取 OFweek
        """
        try:
            logger.info(f"开始爬取 OFweek: {keyword}")
            url = f"https://www.ofweek.com/s/s.shtml?q={quote(keyword)}&type=1"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            items = soup.select('div.list-detail')
            
            for item in items[:max_results]:
                try:
                    title_tag = item.select_one('h3 a')
                    title = title_tag.get_text(strip=True)
                    link = title_tag['href']
                    
                    desc_tag = item.select_one('p.intro')
                    content = desc_tag.get_text(strip=True) if desc_tag else title
                    
                    if not title: continue
                        
                    results.append({
                        'title': title,
                        'content': content,
                        'source': 'crawler_ofweek',
                        'keyword': keyword,
                        'url': link,
                        'crawled_at': datetime.now()
                    })
                except Exception:
                    continue
                    
            logger.info(f"OFweek 爬取完成: {len(results)} 条")
            return results
        except Exception as e:
            logger.error(f"爬取 OFweek 失败: {e}")
            return []
    
    def crawl_all_sources(self, keyword: str) -> List[Dict]:
        """从所有数据源爬取新闻"""
        all_news = []
        
        # 1. 新浪新闻
        all_news.extend(self.crawl_sina_finance(keyword, max_results=5))
        
        # 2. 36氪 (通过百度搜索)
        all_news.extend(self.crawl_36kr(keyword, max_results=5))
        
        # 3. 百度新闻 (通用)
        all_news.extend(self.crawl_robot_news(keyword, max_results=5))
        
        # 4. OFweek
        try:
            all_news.extend(self.crawl_ofweek_robot(keyword, max_results=5))
        except Exception:
            pass
        
        logger.info(f"关键词 '{keyword}' 总共爬取: {len(all_news)} 条新闻")
        return all_news

# 全局爬虫实例
news_crawler = IndustryNewsCrawler()