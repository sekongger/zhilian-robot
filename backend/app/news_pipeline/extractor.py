"""Extraction logic for news pipeline."""

from __future__ import annotations

from typing import Dict, List, Any
import logging
import json
from app.nlp.llm import LLMProcessor
from config.settings import settings

logger = logging.getLogger(__name__)


class NewsPipelineExtractor:
    """Wrapper around LLMProcessor with additional sentiment support."""

    def __init__(self):
        self.llm = LLMProcessor()

    def extract(self, content: str) -> Dict[str, Any]:
        if not content:
            return {"entities": {}, "relations": [], "temporal": {}, "sentiment": {"polarity": 0.0, "intensity": 0.0}}

        result = self.llm.analyze_industry_chain(content)
        temporal = self.llm.extract_temporal_info(content)
        sentiment = self._extract_sentiment(content)

        return {
            "entities": result.get("entities", {}),
            "relations": result.get("relations", []),
            "summary": result.get("summary"),
            "temporal": temporal,
            "sentiment": sentiment,
            "model": settings.OPENAI_MODEL,
        }

    def _extract_sentiment(self, content: str) -> Dict[str, Any]:
        if not self.llm.client:
            return {"polarity": 0.0, "intensity": 0.0, "label": "neutral"}

        prompt = f"""
请判断以下产业资讯文本的情感倾向，返回JSON：
文本：{content}

要求：
- polarity: 正面为1，负面为-1，中性为0（可为小数）
- intensity: 强度0-1
- label: positive/neutral/negative
只返回JSON。
"""
        try:
            response = self.llm.client.chat.completions.create(
                model=self.llm.model,
                messages=[
                    {"role": "system", "content": "你是情感分析助手，只返回JSON。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            result = response.choices[0].message.content.strip()
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result
            if result.endswith("```"):
                result = result.rsplit("\n", 1)[0] if "\n" in result else result
            result = result.strip()
            return json.loads(result)
        except Exception as exc:
            logger.error(f"情感抽取失败: {exc}")
            return {"polarity": 0.0, "intensity": 0.0, "label": "neutral"}

