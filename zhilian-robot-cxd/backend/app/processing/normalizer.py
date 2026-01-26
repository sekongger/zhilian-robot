"""
数据标准化器 - 规范化各种格式的数据
"""
import re
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    数据标准化器
    
    用于规范化日期、公司名称、数据源名称等
    """
    
    # 公司名称后缀
    COMPANY_SUFFIXES = [
        '股份有限公司', '有限责任公司', '有限公司', 
        '集团有限公司', '集团股份有限公司', '集团',
        '控股有限公司', '控股', '科技', '技术',
        '(中国)', '（中国）', 'Co., Ltd.', 'Co.,Ltd.',
        'Inc.', 'Corp.', 'Corporation', 'Limited', 'Ltd.',
        'LLC', 'L.L.C.'
    ]
    
    # 数据源名称映射
    SOURCE_NAME_MAP = {
        # RSS源
        'rss_ithome': 'IT之家',
        'rss_36kr': '36氪',
        'rss_cnbeta': 'CNBeta',
        'rss_ifanr': '爱范儿',
        'rss_leiphone': '雷锋网',
        'rss_mit_tech': 'MIT科技评论',
        
        # 爬虫源
        'crawler_baidu': '百度资讯',
        'crawler_sina': '新浪新闻',
        'crawler_36kr': '36氪',
        'crawler_ofweek': 'OFweek',
        
        # 文件上传
        'file_upload': '文件上传',
        'pdf_upload': 'PDF文件',
        'excel_upload': 'Excel文件',
        'csv_upload': 'CSV文件',
        
        # API接入
        'api': 'API接入'
    }
    
    # 中文日期关键词
    DATE_KEYWORDS = {
        '今天': 0,
        '昨天': -1,
        '前天': -2,
        '明天': 1,
        '后天': 2,
        '本周': 0,
        '上周': -7,
        '本月': 0,
        '上月': -30,
        '今年': 0,
        '去年': -365,
    }
    
    def __init__(self):
        pass
    
    def normalize_date(self, date_str: str, default: datetime = None) -> Optional[datetime]:
        """
        标准化日期格式
        
        支持多种中英文日期格式
        
        Args:
            date_str: 日期字符串
            default: 默认日期(无法解析时返回)
            
        Returns:
            datetime对象或None
        """
        if not date_str:
            return default
        
        date_str = date_str.strip()
        
        # 尝试处理中文日期关键词
        for keyword, days_offset in self.DATE_KEYWORDS.items():
            if keyword in date_str:
                from datetime import timedelta
                return datetime.now() + timedelta(days=days_offset)
        
        # 尝试处理中文格式: 2024年12月15日
        chinese_date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_str)
        if chinese_date_match:
            try:
                year, month, day = chinese_date_match.groups()
                return datetime(int(year), int(month), int(day))
            except ValueError:
                pass
        
        # 尝试处理相对时间: X分钟前, X小时前, X天前
        relative_patterns = [
            (r'(\d+)\s*分钟前', lambda m: datetime.now() - __import__('datetime').timedelta(minutes=int(m.group(1)))),
            (r'(\d+)\s*小时前', lambda m: datetime.now() - __import__('datetime').timedelta(hours=int(m.group(1)))),
            (r'(\d+)\s*天前', lambda m: datetime.now() - __import__('datetime').timedelta(days=int(m.group(1)))),
            (r'(\d+)\s*周前', lambda m: datetime.now() - __import__('datetime').timedelta(weeks=int(m.group(1)))),
            (r'(\d+)\s*个?月前', lambda m: datetime.now() - __import__('datetime').timedelta(days=int(m.group(1)) * 30)),
        ]
        
        for pattern, handler in relative_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return handler(match)
                except Exception:
                    pass
        
        # 使用dateutil解析
        try:
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            pass
        
        return default
    
    def normalize_company_name(self, name: str) -> str:
        """
        标准化公司名称
        
        - 去除多余空白
        - 规范化标点
        - 保留简称
        
        Args:
            name: 公司名称
            
        Returns:
            标准化后的名称
        """
        if not name:
            return ""
        
        name = name.strip()
        
        # 规范化空白
        name = re.sub(r'\s+', '', name)
        
        # 规范化括号
        name = name.replace('（', '(').replace('）', ')')
        
        # 移除可能的引号
        name = name.strip('"\'""''')
        
        return name
    
    def extract_company_short_name(self, full_name: str) -> str:
        """
        提取公司简称
        
        Args:
            full_name: 公司全称
            
        Returns:
            简称
        """
        if not full_name:
            return ""
        
        short_name = full_name
        
        # 移除常见后缀
        for suffix in self.COMPANY_SUFFIXES:
            if short_name.endswith(suffix):
                short_name = short_name[:-len(suffix)]
                break
        
        # 移除地区前缀
        location_prefixes = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉']
        for prefix in location_prefixes:
            if short_name.startswith(prefix):
                short_name = short_name[len(prefix):]
                break
        
        return short_name.strip()
    
    def normalize_source(self, source: str) -> str:
        """
        标准化数据源名称
        
        Args:
            source: 原始数据源标识
            
        Returns:
            标准化的数据源名称
        """
        if not source:
            return "未知来源"
        
        # 查找映射
        normalized = self.SOURCE_NAME_MAP.get(source)
        if normalized:
            return normalized
        
        # 尝试模糊匹配
        source_lower = source.lower()
        for key, value in self.SOURCE_NAME_MAP.items():
            if key in source_lower or source_lower in key:
                return value
        
        # 返回原值
        return source
    
    def normalize_url(self, url: str) -> str:
        """
        标准化URL
        
        - 添加协议头
        - 移除追踪参数
        - 规范化编码
        
        Args:
            url: 原始URL
            
        Returns:
            标准化的URL
        """
        if not url:
            return ""
        
        url = url.strip()
        
        # 添加协议头
        if not url.startswith(('http://', 'https://', 'file://')):
            url = 'https://' + url
        
        # 移除常见追踪参数
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                          'utm_content', 'from', 'isappinstalled', 'scene']
        
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # 移除追踪参数
            cleaned_params = {k: v for k, v in query_params.items() 
                            if k.lower() not in tracking_params}
            
            # 重建URL
            new_query = urlencode(cleaned_params, doseq=True)
            cleaned_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                ''  # 移除fragment
            ))
            
            return cleaned_url
            
        except Exception:
            return url
    
    def normalize_text_length(self, text: str, max_length: int = 5000, 
                             suffix: str = "...") -> str:
        """
        规范化文本长度
        
        Args:
            text: 原始文本
            max_length: 最大长度
            suffix: 截断后缀
            
        Returns:
            规范化后的文本
        """
        if not text or len(text) <= max_length:
            return text or ""
        
        # 尝试在句子边界截断
        truncated = text[:max_length]
        
        # 找到最后一个句号、问号或感叹号
        last_sentence_end = max(
            truncated.rfind('。'),
            truncated.rfind('？'),
            truncated.rfind('！'),
            truncated.rfind('.'),
            truncated.rfind('?'),
            truncated.rfind('!')
        )
        
        if last_sentence_end > max_length * 0.7:  # 至少保留70%
            return truncated[:last_sentence_end + 1]
        
        return truncated + suffix
    
    def extract_numbers(self, text: str) -> List[Dict]:
        """
        提取文本中的数字信息
        
        Args:
            text: 文本
            
        Returns:
            数字信息列表
        """
        results = []
        
        # 匹配带单位的数字
        patterns = [
            # 金额
            (r'(\d+(?:\.\d+)?)\s*(亿|万|千|百)?(?:美元|美金|USD|\$)', 'currency_usd'),
            (r'(\d+(?:\.\d+)?)\s*(亿|万|千|百)?(?:元|人民币|RMB|￥)', 'currency_cny'),
            
            # 百分比
            (r'(\d+(?:\.\d+)?)\s*[%％]', 'percentage'),
            
            # 数量
            (r'(\d+(?:\.\d+)?)\s*(亿|万|千|百)?(?:台|个|件|套)', 'quantity'),
            
            # 年份
            (r'(20\d{2}|19\d{2})年', 'year'),
        ]
        
        for pattern, num_type in patterns:
            for match in re.finditer(pattern, text):
                results.append({
                    'value': match.group(0),
                    'type': num_type,
                    'position': match.start()
                })
        
        return results
