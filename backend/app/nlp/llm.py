"""
NLP模块 - 大语言模型集成
"""
from typing import List, Dict, Optional, Iterator
import logging
import json
from config.settings import settings

logger = logging.getLogger(__name__)

# 尝试导入OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI库未安装,部分功能将不可用")


class LLMProcessor:
    """大语言模型处理器"""
    
    def __init__(self):
        self.client = None
        self.model = settings.OPENAI_MODEL
        
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            # 使用 DeepSeek API (兼容 OpenAI 接口)
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE
            )
    
    def extract_entities_with_llm(self, text: str) -> Dict:
        """
        使用大模型提取实体
        
        Args:
            text: 输入文本
            
        Returns:
            提取的实体信息
        """
        if not self.client:
            logger.error("OpenAI客户端未初始化")
            return {}
        
        prompt = f"""
        请从以下文本中提取机器人产业链相关的实体信息:
        
        文本: {text}
        
        请提取以下类型的实体:
        1. 企业名称
        2. 产品名称
        3. 技术名称
        4. 关键人物
        5. 地点
        
        以JSON格式返回,格式如下:
        {{
            "companies": ["企业1", "企业2"],
            "products": ["产品1", "产品2"],
            "technologies": ["技术1", "技术2"],
            "persons": ["人物1", "人物2"],
            "locations": ["地点1", "地点2"]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的产业链分析助手,擅长从文本中提取实体信息。只返回JSON,不要包含任何其他文本或Markdown标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            # 清理可能的Markdown代码块标记
            result = result.strip()
            if result.startswith("```"):
                # 移除 ```json 或 ``` 开头
                result = result.split('\n', 1)[1] if '\n' in result else result
            if result.endswith("```"):
                # 移除 ``` 结尾
                result = result.rsplit('\n', 1)[0] if '\n' in result else result
            result = result.strip()
            
            logger.info(f"LLM实体提取结果: {result[:200]}...")
            return json.loads(result)
        except Exception as e:
            logger.error(f"LLM实体提取失败: {str(e)}, 原始响应: {response.choices[0].message.content if 'response' in locals() else 'N/A'}")
            return {}
    
    def extract_relations_with_llm(self, text: str, entities: Dict) -> List[Dict]:
        """
        使用大模型提取关系
        
        Args:
            text: 输入文本
            entities: 已提取的实体
            
        Returns:
            关系列表
        """
        if not self.client:
            logger.error("OpenAI客户端未初始化")
            return []
        
        prompt = f"""
        基于以下文本和已识别的实体,请提取它们之间的产业链关系:
        
        文本: {text}
        
        实体: {entities}
        
        请识别以下类型的关系:
        - 供应关系(供应商-客户)
        - 合作关系
        - 竞争关系
        - 投资关系
        - 上下游关系
        
        以JSON格式返回关系列表,格式如下:
        [
            {{
                "subject": "实体1",
                "relation": "关系类型",
                "object": "实体2",
                "confidence": 0.9
            }}
        ]
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的产业链关系分析专家。只返回JSON数组,不要包含任何其他文本或Markdown标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            # 清理可能的Markdown代码块标记
            result = result.strip()
            if result.startswith("```"):
                result = result.split('\n', 1)[1] if '\n' in result else result
            if result.endswith("```"):
                result = result.rsplit('\n', 1)[0] if '\n' in result else result
            result = result.strip()
            
            logger.info(f"LLM关系提取结果: {result[:200]}...")
            return json.loads(result)
        except Exception as e:
            logger.error(f"LLM关系提取失败: {str(e)}, 原始响应: {response.choices[0].message.content if 'response' in locals() else 'N/A'}")
            return []
    
    def analyze_industry_chain(self, text: str) -> Dict:
        """
        综合分析产业链结构
        
        Args:
            text: 输入文本
            
        Returns:
            产业链分析结果
        """
        entities = self.extract_entities_with_llm(text)
        relations = self.extract_relations_with_llm(text, entities)
        
        return {
            "entities": entities,
            "relations": relations,
            "summary": self._generate_summary(entities, relations)
        }
    
    def _generate_summary(self, entities: Dict, relations: List[Dict]) -> str:
        """生成分析摘要"""
        company_count = len(entities.get("companies", []))
        relation_count = len(relations)
        
        return f"识别到{company_count}家企业,发现{relation_count}个关系"
    
    # ==================== 新增：时间分析相关方法 ====================
    
    def extract_temporal_info(self, text: str) -> Dict:
        """
        提取文本中的时间信息
        
        Args:
            text: 输入文本
            
        Returns:
            时间信息字典 {
                "absolute_time": "2024-12-15",
                "relative_time": "明年",
                "event_type": "FUTURE",
                "confidence": 0.9
            }
        """
        if not self.client:
            logger.error("OpenAI客户端未初始化")
            return {}
        
        prompt = f"""
        请从以下文本中提取时间信息:
        
        文本: {text}
        
        请识别:
        1. 绝对时间（如"2024年12月15日"）
        2. 相对时间（如"明年"、"下个月"、"昨天"）
        3. 事件时态（PAST/PRESENT/FUTURE）
        4. 置信度（0-1之间的浮点数）
        
        以JSON格式返回:
        {{
            "absolute_time": "2024-12-15T00:00:00" 或 null,
            "relative_time": "明年" 或 null,
            "event_type": "PAST/PRESENT/FUTURE",
            "confidence": 0.9,
            "description": "时间描述"
        }}
        
        注意：如果文本中没有明确的时间信息，返回event_type为PRESENT，confidence为0.5
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个时间信息提取专家。只返回JSON，不要包含任何其他文本或Markdown标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            result = response.choices[0].message.content
            result = result.strip()
            if result.startswith("```"):
                result = result.split('\n', 1)[1] if '\n' in result else result
            if result.endswith("```"):
                result = result.rsplit('\n', 1)[0] if '\n' in result else result
            result = result.strip()
            
            temporal_info = json.loads(result)
            logger.info(f"时间提取成功: {temporal_info}")
            return temporal_info
        except Exception as e:
            logger.error(f"时间提取失败: {e}")
            return {
                "absolute_time": None,
                "relative_time": None,
                "event_type": "PRESENT",
                "confidence": 0.5
            }
    
    def extract_sentiment(self, text: str) -> Dict:
        """
        提取文本情感信息
        
        Args:
            text: 输入文本
            
        Returns:
            情感分析结果 {
                "polarity": 0.8,  # -1(负面) 到 1(正面)
                "intensity": 0.6,  # 0(弱) 到 1(强)
                "confidence": 0.9
            }
        """
        if not self.client:
            logger.error("OpenAI客户端未初始化")
            return {}
        
        prompt = f"""
        请分析以下文本的情感倾向:
        
        文本: {text}
        
        请评估:
        1. 情感极性（polarity）: -1（非常负面）到 1（非常正面），0为中性
        2. 情感强度（intensity）: 0（情感很弱）到 1（情感很强）
        3. 分析置信度（confidence）: 0到1之间
        
        以JSON格式返回:
        {{
            "polarity": 0.8,
            "intensity": 0.6,
            "confidence": 0.9,
            "keywords": ["关键词1", "关键词2"],
            "summary": "简短的情感分析总结"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个情感分析专家。只返回JSON，不要包含任何其他文本或Markdown标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            
            result = response.choices[0].message.content
            result = result.strip()
            if result.startswith("```"):
                result = result.split('\n', 1)[1] if '\n' in result else result
            if result.endswith("```"):
                result = result.rsplit('\n', 1)[0] if '\n' in result else result
            result = result.strip()
            
            sentiment = json.loads(result)
            logger.info(f"情感分析成功: polarity={sentiment.get('polarity')}, intensity={sentiment.get('intensity')}")
            return sentiment
        except Exception as e:
            logger.error(f"情感分析失败: {e}")
            return {
                "polarity": 0.0,
                "intensity": 0.0,
                "confidence": 0.5
            }
    
    def analyze_with_temporal_and_sentiment(self, text: str) -> Dict:
        """
        综合分析：实体+关系+时间+情感
        
        Args:
            text: 输入文本
            
        Returns:
            完整的分析结果
        """
        # 提取实体和关系
        entities = self.extract_entities_with_llm(text)
        relations = self.extract_relations_with_llm(text, entities)
        
        # 提取时间信息
        temporal_info = self.extract_temporal_info(text)
        
        # 提取情感信息
        sentiment = self.extract_sentiment(text)
        
        return {
            "entities": entities,
            "relations": relations,
            "temporal_info": temporal_info,
            "sentiment": sentiment,
            "summary": self._generate_summary(entities, relations)
        }
    
    def generate_text(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        使用大模型生成文本
        
        Args:
            prompt: 提示词
            max_tokens: 最大生成token数
            
        Returns:
            生成的文本内容
        """
        if not self.client:
            logger.warning("LLM客户端未初始化,使用默认回复")
            return "AI简报生成功能需要配置DeepSeek API密钥。请检查配置文件。"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据分析师，擅长撰写简洁专业的分析报告。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM文本生成失败: {e}", exc_info=True)
            return f"AI简报生成失败: {str(e)}"

    def generate_text_stream(self, prompt: str, max_tokens: int = 1000) -> Iterator[str]:
        """
        使用大模型进行真正的 token 级流式生成

        Args:
            prompt: 提示词
            max_tokens: 最大生成token数

        Yields:
            流式文本片段
        """
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你是一个专业的数据分析师，擅长撰写简洁专业的分析报告。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            stream=True,
        )

        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if isinstance(content, str) and content:
                yield content
                continue
            if isinstance(content, list):
                text = "".join(
                    str(getattr(part, "text", "") or "")
                    for part in content
                )
                if text:
                    yield text


# 全局LLM处理器实例
llm_processor = LLMProcessor()
