"""
数据清洗器 - 清洗原始数据中的噪声和无用信息
"""
import re
import logging
from typing import Optional
from bs4 import BeautifulSoup
import html

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    数据清洗器
    
    用于清洗从各种数据源获取的原始数据
    """
    
    # 常见的样板文本模式
    BOILERPLATE_PATTERNS = [
        r'版权所有.*?保留.*?权利',
        r'Copyright.*?All [Rr]ights [Rr]eserved',
        r'本文来源[:：].*',
        r'转载请注明.*',
        r'责任编辑[:：].*',
        r'编辑[:：]\s*\w+\s*$',
        r'记者[:：].*',
        r'来源[:：]\s*(新华社|中新网|央视|人民日报).*',
        r'关注.*?公众号.*',
        r'点击.*?阅读原文.*',
        r'扫.*?二维码.*',
        r'更多精彩.*?关注.*',
        r'(原标题[:：]|原题[:：]).*',
        r'\[.*?编辑.*?\]',
        r'【.*?编辑.*?】',
    ]
    
    # 无意义的短语
    NOISE_PHRASES = [
        '点击这里', '了解更多', '阅读更多', '查看详情',
        '立即订阅', '免费试用', '点击查看', '点击进入',
        '分享到', '收藏本文', '打印本页', '返回顶部',
    ]
    
    def __init__(self):
        # 编译正则表达式
        self._boilerplate_regex = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) 
            for p in self.BOILERPLATE_PATTERNS
        ]
    
    def clean_html(self, html_content: str) -> str:
        """
        清洗HTML，提取纯文本
        
        Args:
            html_content: HTML字符串
            
        Returns:
            清洗后的纯文本
        """
        if not html_content:
            return ""
        
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除脚本和样式标签
            for tag in soup.find_all(['script', 'style', 'noscript', 'iframe', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # 移除注释
            for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.new_string('')))):
                if hasattr(comment, 'is_comment') and comment.is_comment:
                    comment.extract()
            
            # 提取文本
            text = soup.get_text(separator='\n')
            
            # 清洗文本
            return self.clean_text(text)
            
        except Exception as e:
            logger.error(f"HTML清洗失败: {e}")
            return html_content
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        
        - 去除特殊字符
        - 规范化空白
        - 移除重复行
        - 修复编码问题
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        
        # 1. 解码HTML实体
        text = html.unescape(text)
        
        # 2. 规范化Unicode
        text = self._normalize_unicode(text)
        
        # 3. 移除控制字符 (保留换行和制表符)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # 4. 规范化空白字符
        text = self._normalize_whitespace(text)
        
        # 5. 移除重复行
        text = self._remove_duplicate_lines(text)
        
        # 6. 移除过短的行 (可能是噪声)
        lines = text.split('\n')
        lines = [line for line in lines if len(line.strip()) >= 2 or line.strip() == '']
        text = '\n'.join(lines)
        
        return text.strip()
    
    def remove_boilerplate(self, text: str) -> str:
        """
        移除样板文本
        
        如广告、版权声明、导航链接等
        
        Args:
            text: 原始文本
            
        Returns:
            移除样板后的文本
        """
        if not text:
            return ""
        
        # 应用样板匹配规则
        for pattern in self._boilerplate_regex:
            text = pattern.sub('', text)
        
        # 移除噪声短语
        for phrase in self.NOISE_PHRASES:
            text = text.replace(phrase, '')
        
        # 清理产生的空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def fix_encoding(self, content: bytes, declared_encoding: str = None) -> str:
        """
        修复编码问题
        
        尝试多种编码方式解码文本
        
        Args:
            content: 原始字节数据
            declared_encoding: 声明的编码
            
        Returns:
            解码后的文本
        """
        # 尝试的编码顺序
        encodings_to_try = []
        
        if declared_encoding:
            encodings_to_try.append(declared_encoding)
        
        # 使用chardet检测
        try:
            import chardet
            detected = chardet.detect(content)
            if detected['encoding']:
                encodings_to_try.append(detected['encoding'])
        except ImportError:
            pass
        
        # 常用编码
        encodings_to_try.extend(['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1'])
        
        # 去重保持顺序
        seen = set()
        unique_encodings = []
        for enc in encodings_to_try:
            if enc and enc.lower() not in seen:
                seen.add(enc.lower())
                unique_encodings.append(enc)
        
        # 尝试解码
        for encoding in unique_encodings:
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 最后尝试: 忽略错误
        return content.decode('utf-8', errors='ignore')
    
    def _normalize_unicode(self, text: str) -> str:
        """规范化Unicode字符"""
        import unicodedata
        # NFC规范化
        text = unicodedata.normalize('NFC', text)
        
        # 全角转半角 (数字和字母)
        result = []
        for char in text:
            code = ord(char)
            # 全角空格
            if code == 0x3000:
                result.append(' ')
            # 全角ASCII字符
            elif 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将多个空格/制表符替换为单个空格
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 将3个及以上连续换行替换为2个
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 去除每行首尾空白
        lines = text.split('\n')
        lines = [line.strip() for line in lines]
        
        return '\n'.join(lines)
    
    def _remove_duplicate_lines(self, text: str) -> str:
        """移除连续重复行"""
        lines = text.split('\n')
        result = []
        prev_line = None
        
        for line in lines:
            # 跳过连续重复行
            if line != prev_line or not line.strip():
                result.append(line)
            prev_line = line
        
        return '\n'.join(result)
    
    def extract_main_content(self, text: str, min_paragraph_length: int = 50) -> str:
        """
        提取主要内容
        
        过滤掉短段落，保留主体内容
        
        Args:
            text: 原始文本
            min_paragraph_length: 最小段落长度
            
        Returns:
            主要内容
        """
        paragraphs = text.split('\n\n')
        main_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if len(para) >= min_paragraph_length:
                main_paragraphs.append(para)
        
        return '\n\n'.join(main_paragraphs)


# 便捷函数
def clean_html(html_content: str) -> str:
    """便捷函数: 清洗HTML"""
    cleaner = DataCleaner()
    return cleaner.clean_html(html_content)


def clean_text(text: str) -> str:
    """便捷函数: 清洗文本"""
    cleaner = DataCleaner()
    return cleaner.clean_text(text)
