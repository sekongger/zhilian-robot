from __future__ import annotations

from dataclasses import dataclass

from crawler.utils.text_utils import normalize_text

ROBOTICS_KEYWORDS = {
    "机器人",
    "人形机器人",
    "工业机器人",
    "协作机器人",
    "具身智能",
    "机械臂",
    "自动化产线",
    "AGV",
    "AMR",
    "减速器",
    "谐波减速器",
    "RV减速器",
    "伺服电机",
    "伺服驱动",
    "机器视觉",
    "激光雷达",
    "控制器",
}


@dataclass(slots=True)
class RelevanceResult:
    passed: bool
    score: float
    matched_keywords: list[str]


def evaluate_relevance(title: str, content: str, mode: str = "high_recall") -> RelevanceResult:
    title_text = normalize_text(title).lower()
    content_text = normalize_text(content).lower()

    matched: list[str] = []
    score = 0.0
    for keyword in sorted(ROBOTICS_KEYWORDS):
        lower_keyword = keyword.lower()
        title_hit = lower_keyword in title_text
        body_hit = lower_keyword in content_text
        if title_hit or body_hit:
            matched.append(keyword)
            score += 2.0 if title_hit else 1.0

    threshold = 1.0 if mode == "high_recall" else 2.0
    return RelevanceResult(passed=score >= threshold, score=score, matched_keywords=matched)

