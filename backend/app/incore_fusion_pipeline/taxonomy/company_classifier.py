"""Company concept classification rules shared by pipeline and evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from app.incore_fusion_pipeline.utils import normalize_text_key


COMPANY_CATEGORY_PARENT_MAP: Dict[str, str] = {
    "科技企业": "科技创新企业",
    "软件信息企业": "科技创新企业",
    "人工智能企业": "科技创新企业",
    "制造企业": "先进制造企业",
    "高端装备企业": "先进制造企业",
    "新材料企业": "先进制造企业",
    "商贸企业": "商贸流通企业",
    "贸易企业": "商贸流通企业",
    "企业服务企业": "专业服务企业",
    "工程建设企业": "工程建设企业",
    "农业食品企业": "农业食品企业",
    "医疗健康企业": "医疗健康企业",
    "物流供应链企业": "物流供应链企业",
    "能源环保企业": "能源环保企业",
    "金融投资企业": "金融投资企业",
    "文化消费企业": "文化消费企业",
    "科技创新企业": "企业分类",
    "先进制造企业": "企业分类",
    "商贸流通企业": "企业分类",
    "专业服务企业": "企业分类",
    "工程建设企业": "企业分类",
    "农业食品企业": "企业分类",
    "医疗健康企业": "企业分类",
    "物流供应链企业": "企业分类",
    "能源环保企业": "企业分类",
    "金融投资企业": "企业分类",
    "文化消费企业": "企业分类",
}

INDUSTRY_SECTOR_PARENT_MAP: Dict[str, str] = {
    "人工智能": "数字经济",
    "电子信息": "数字经济",
    "高端装备": "制造业",
    "半导体": "电子信息",
    "新能源": "能源",
    "汽车": "制造业",
    "生物医药": "生命健康",
    "新材料": "制造业",
    "建筑建材": "制造业",
    "现代农业": "生命健康",
    "食品消费": "生命健康",
    "现代服务": "数字经济",
    "现代物流": "数字经济",
    "生态环保": "能源",
}


@dataclass(frozen=True)
class KeywordRule:
    """Weighted keyword rule for a single concept."""

    concept_name: str
    parent_name: str | None = None
    name_keywords: Tuple[str, ...] = ()
    text_keywords: Tuple[str, ...] = ()
    negative_keywords: Tuple[str, ...] = ()
    base_score: float = 0.58
    name_weight: float = 0.12
    text_weight: float = 0.06
    min_name_hits: int = 0
    min_text_hits: int = 1
    min_total_hits: int = 1


@dataclass(frozen=True)
class PredictedConcept:
    """Prediction with score and matched terms."""

    concept_type: str
    concept_name: str
    score: float
    matched_terms: Tuple[str, ...] = field(default_factory=tuple)
    parent_name: str | None = None


class CompanyConceptClassifier:
    """Rule-based classifier for company categories and industry sectors."""

    COMPANY_CATEGORY_RULES: Tuple[KeywordRule, ...] = (
        KeywordRule(
            concept_name="人工智能企业",
            parent_name="科技创新企业",
            name_keywords=("人工智能", "智能科技", "智能系统", "智能机器人"),
            text_keywords=("人工智能", "大模型", "机器学习", "计算机视觉", "自然语言处理", "智能算法", "机器人控制"),
            base_score=0.72,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="软件信息企业",
            parent_name="科技创新企业",
            name_keywords=("软件", "信息", "网络", "数据", "云", "数字", "系统"),
            text_keywords=("软件开发", "信息技术", "网络技术", "数据处理", "云计算", "系统集成", "平台开发", "信息系统"),
            base_score=0.68,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="科技企业",
            parent_name="科技创新企业",
            name_keywords=("科技", "技术", "研发"),
            text_keywords=("技术开发", "技术服务", "技术咨询", "技术转让", "技术推广", "研发"),
            base_score=0.66,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="高端装备企业",
            parent_name="先进制造企业",
            name_keywords=("装备", "机电", "自动化", "机器人", "仪器"),
            text_keywords=("机器人", "自动化", "伺服", "控制器", "机床", "数控", "仪器仪表", "智能装备"),
            base_score=0.72,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="新材料企业",
            parent_name="先进制造企业",
            name_keywords=("材料", "新材", "高分子", "碳纤维"),
            text_keywords=("新材料", "复合材料", "高分子", "碳纤维", "合金材料", "纳米材料"),
            base_score=0.70,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="制造企业",
            parent_name="先进制造企业",
            name_keywords=("制造", "实业", "工业"),
            text_keywords=("制造", "生产", "加工", "工业", "工艺品制造", "设备制造"),
            base_score=0.64,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="商贸企业",
            parent_name="商贸流通企业",
            name_keywords=("商贸",),
            text_keywords=("日用百货销售", "批发", "零售", "互联网销售", "商业管理", "国内贸易代理"),
            base_score=0.67,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="贸易企业",
            parent_name="商贸流通企业",
            name_keywords=("贸易", "进出口"),
            text_keywords=("货物进出口", "技术进出口", "进出口代理", "贸易经纪", "国际贸易"),
            base_score=0.68,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="企业服务企业",
            parent_name="专业服务企业",
            name_keywords=("咨询", "管理", "服务", "代理", "策划", "财税", "检测", "认证"),
            text_keywords=("企业管理", "企业管理咨询", "信息咨询", "商务代理", "市场营销策划", "知识产权服务", "检验检测", "认证服务", "技术服务", "人力资源"),
            negative_keywords=("餐饮服务", "居民日常生活服务"),
            base_score=0.62,
            min_text_hits=2,
            min_total_hits=2,
        ),
        KeywordRule(
            concept_name="工程建设企业",
            parent_name="工程建设企业",
            name_keywords=("建筑", "建设", "工程", "装饰", "安装", "园林"),
            text_keywords=("建设工程", "施工", "装饰装修", "工程管理", "园林绿化", "安装服务", "市政工程"),
            base_score=0.70,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="农业食品企业",
            parent_name="农业食品企业",
            name_keywords=("农业", "生态农业", "食品", "餐饮", "酒业", "养殖", "种植"),
            text_keywords=("农业", "种植", "养殖", "农产品", "食品销售", "餐饮服务", "畜牧", "水产"),
            base_score=0.69,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="医疗健康企业",
            parent_name="医疗健康企业",
            name_keywords=("医药", "医疗", "健康", "器械", "诊所"),
            text_keywords=("医疗器械", "医药", "制药", "健康咨询", "诊疗", "药品", "生物制品"),
            base_score=0.72,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="物流供应链企业",
            parent_name="物流供应链企业",
            name_keywords=("物流", "仓储", "货运", "运输", "供应链", "冷链"),
            text_keywords=("道路货物运输", "仓储", "配送", "供应链管理", "货运代理", "冷链"),
            base_score=0.70,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="能源环保企业",
            parent_name="能源环保企业",
            name_keywords=("能源", "环保", "节能", "环境", "光伏", "电力"),
            text_keywords=("新能源", "光伏", "储能", "节能", "环境保护", "污水处理", "碳"),
            base_score=0.70,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="金融投资企业",
            parent_name="金融投资企业",
            name_keywords=("投资", "资本", "基金", "资管", "保理"),
            text_keywords=("投资", "资产管理", "基金管理", "融资租赁", "保理"),
            base_score=0.74,
            min_text_hits=1,
        ),
        KeywordRule(
            concept_name="文化消费企业",
            parent_name="文化消费企业",
            name_keywords=("文化", "传媒", "广告", "教育", "旅游", "酒店", "娱乐"),
            text_keywords=("广告设计", "广告发布", "教育培训", "文化传播", "旅游", "酒店管理", "演出"),
            base_score=0.68,
            min_text_hits=1,
        ),
    )

    INDUSTRY_RULES: Tuple[KeywordRule, ...] = (
        KeywordRule("人工智能", "数字经济", name_keywords=("人工智能",), text_keywords=("人工智能", "大模型", "机器学习", "计算机视觉", "自然语言处理"), base_score=0.76),
        KeywordRule("电子信息", "数字经济", name_keywords=("软件", "信息", "网络", "数据", "通信", "电子"), text_keywords=("信息技术", "软件开发", "系统集成", "数据处理", "通信设备", "电子元器件"), base_score=0.68),
        KeywordRule("高端装备", "制造业", name_keywords=("装备", "机器人", "自动化", "机电", "仪器"), text_keywords=("机器人", "自动化", "伺服", "控制器", "机床", "仪器仪表", "智能装备"), base_score=0.74),
        KeywordRule("半导体", "电子信息", name_keywords=("半导体", "芯片", "集成电路"), text_keywords=("半导体", "芯片", "集成电路", "晶圆", "封装测试"), base_score=0.78),
        KeywordRule("新能源", "能源", name_keywords=("新能源", "光伏", "储能", "电池"), text_keywords=("新能源", "储能", "光伏", "锂电", "氢能", "电池"), base_score=0.74),
        KeywordRule("汽车", "制造业", name_keywords=("汽车", "汽配", "车业"), text_keywords=("汽车零部件", "整车", "汽配", "新能源汽车"), base_score=0.72),
        KeywordRule("生物医药", "生命健康", name_keywords=("医药", "医疗", "生物", "健康"), text_keywords=("医药", "制药", "医疗器械", "生物技术", "健康服务"), base_score=0.76),
        KeywordRule("新材料", "制造业", name_keywords=("材料", "新材", "高分子"), text_keywords=("新材料", "复合材料", "高分子", "碳纤维", "纳米材料"), base_score=0.74),
        KeywordRule("建筑建材", "制造业", name_keywords=("建筑", "建材", "建设"), text_keywords=("建设工程", "建筑材料", "施工", "装饰装修"), base_score=0.70),
        KeywordRule("现代农业", "生命健康", name_keywords=("农业", "种植", "养殖"), text_keywords=("农业", "种植", "养殖", "农产品", "畜牧", "水产"), base_score=0.70),
        KeywordRule("食品消费", "生命健康", name_keywords=("食品", "餐饮", "饮料", "酒业"), text_keywords=("食品销售", "餐饮服务", "饮料", "酒", "预包装食品"), base_score=0.68),
        KeywordRule("现代服务", "数字经济", name_keywords=("咨询", "管理", "服务", "策划"), text_keywords=("企业管理咨询", "信息咨询", "商务服务", "知识产权服务", "检验检测"), base_score=0.60, min_text_hits=2, min_total_hits=2),
        KeywordRule("现代物流", "数字经济", name_keywords=("物流", "货运", "仓储", "供应链"), text_keywords=("物流", "仓储", "运输", "配送", "供应链管理", "冷链"), base_score=0.72),
        KeywordRule("生态环保", "能源", name_keywords=("环保", "环境", "节能"), text_keywords=("环境保护", "污水处理", "节能", "固废", "碳"), base_score=0.72),
    )

    def classify_company(
        self,
        *,
        name: str,
        business_scope: str | None = None,
        description: str | None = None,
        limit_categories: int = 3,
        limit_industries: int = 2,
    ) -> Dict[str, List[PredictedConcept]]:
        """Return predicted company categories and industry sectors."""

        name_text = str(name or "")
        detail_text = " ".join(part for part in (business_scope or "", description or "") if part)
        company_categories = self._run_rules(
            concept_type="CompanyCategory",
            rules=self.COMPANY_CATEGORY_RULES,
            name_text=name_text,
            detail_text=detail_text,
            limit=limit_categories,
        )
        industries = self._run_rules(
            concept_type="IndustrySector",
            rules=self.INDUSTRY_RULES,
            name_text=name_text,
            detail_text=detail_text,
            limit=limit_industries,
        )
        return {
            "company_categories": company_categories,
            "industry_sectors": industries,
        }

    def _run_rules(
        self,
        *,
        concept_type: str,
        rules: Iterable[KeywordRule],
        name_text: str,
        detail_text: str,
        limit: int,
    ) -> List[PredictedConcept]:
        predictions: List[PredictedConcept] = []
        for rule in rules:
            predicted = self._score_rule(
                concept_type=concept_type,
                rule=rule,
                name_text=name_text,
                detail_text=detail_text,
            )
            if predicted is not None:
                predictions.append(predicted)
        predictions.sort(key=lambda item: (-item.score, item.concept_name))
        return predictions[:limit]

    def _score_rule(
        self,
        *,
        concept_type: str,
        rule: KeywordRule,
        name_text: str,
        detail_text: str,
    ) -> PredictedConcept | None:
        if any(keyword in name_text or keyword in detail_text for keyword in rule.negative_keywords):
            return None

        name_hits = self._matched_terms(name_text, rule.name_keywords)
        detail_hits = self._matched_terms(detail_text, rule.text_keywords)
        total_hits = len(name_hits) + len(detail_hits)
        if len(name_hits) < rule.min_name_hits:
            return None
        if not name_hits and len(detail_hits) < rule.min_text_hits:
            return None
        if total_hits < rule.min_total_hits:
            return None

        score = min(
            rule.base_score + len(name_hits) * rule.name_weight + len(detail_hits) * rule.text_weight,
            0.96,
        )
        return PredictedConcept(
            concept_type=concept_type,
            concept_name=rule.concept_name,
            score=round(score, 2),
            matched_terms=tuple(name_hits + detail_hits),
            parent_name=rule.parent_name,
        )

    @staticmethod
    def _matched_terms(text: str, keywords: Iterable[str]) -> List[str]:
        seen = set()
        matched: List[str] = []
        for keyword in keywords:
            normalized_keyword = normalize_text_key(keyword)
            if not normalized_keyword or normalized_keyword in seen:
                continue
            if keyword and keyword in text:
                seen.add(normalized_keyword)
                matched.append(keyword)
        return matched
