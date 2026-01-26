"""
NLP模块初始化
使用DeepSeek LLM进行实体识别和关系抽取
"""
from .llm import llm_processor, LLMProcessor

__all__ = [
    'llm_processor',
    'LLMProcessor'
]
