export const ENTITY_HEAT_TYPE_OPTIONS = [
  { value: 'Enterprise', label: '公司', description: '企业、公司、机构类实体' },
  { value: 'Product', label: '产品', description: '产品、型号、产品词类实体' },
  { value: 'Person', label: '人物', description: '产业人物、创始人、高管、专家' },
  { value: 'Technology', label: '技术', description: '技术、算法、工艺和方案' },
  { value: 'Region', label: '区域', description: '国家、城市、产业区域' },
]

export const PERIOD_OPTIONS = [
  { value: 'daily', label: '每日榜' },
  { value: 'weekly', label: '每周榜' },
]

const DEFAULT_FORMULA = {
  mention_weight: 0.45,
  news_hotness_weight: 0.2,
  source_weight: 0.15,
  freshness_weight: 0.1,
  anchor_weight: 0.1,
}

export const FORMULA_LABELS = [
  {
    key: 'mention_weight',
    name: '提及强度',
    description: '同周期同类型内，实体被多少篇资讯提到；用 log1p 后归一化。',
  },
  {
    key: 'news_hotness_weight',
    name: '关联资讯热度',
    description: '提及该实体的资讯热度总和，体现资讯本身的重要性。',
  },
  {
    key: 'source_weight',
    name: '来源覆盖度',
    description: '不同信息源数量，降低单一来源重复刷屏的影响。',
  },
  {
    key: 'freshness_weight',
    name: '时间新鲜度',
    description: '越接近统计窗口结束时间，贡献越高。',
  },
  {
    key: 'anchor_weight',
    name: '锚点可信度',
    description: '已链接常识锚点得分最高，候选链接居中，未匹配保留但降权。',
  },
]

export function formatHeatScore(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return '0.00'
  }
  return number.toFixed(2)
}

export function buildFormulaRows(formula = DEFAULT_FORMULA) {
  return FORMULA_LABELS.map((item) => {
    const weight = Number(formula[item.key] ?? DEFAULT_FORMULA[item.key] ?? 0)
    return {
      ...item,
      weight,
      weightText: `${Math.round(weight * 100)}%`,
    }
  })
}

export function normalizeRankingResponse(payload = {}) {
  return {
    period_type: payload.period_type || 'daily',
    period_start: payload.period_start || '',
    period_end: payload.period_end || '',
    entity_type: payload.entity_type || 'Enterprise',
    formula_version: payload.formula_version || 'entity_heat_v1',
    formula: { ...DEFAULT_FORMULA, ...(payload.formula || {}) },
    items: Array.isArray(payload.items) ? payload.items : [],
  }
}

export function buildHeatRankingQueryParams({
  periodType = 'daily',
  entityType = 'Enterprise',
  date = null,
  limit = 50,
} = {}) {
  const params = {
    period_type: periodType,
    entity_type: entityType,
    limit,
  }
  if (date?.format) {
    params.date = date.format('YYYY-MM-DD')
  } else if (typeof date === 'string' && date.trim()) {
    params.date = date.trim()
  }
  return params
}

export function getEntityTypeLabel(value) {
  return ENTITY_HEAT_TYPE_OPTIONS.find((item) => item.value === value)?.label || value || '实体'
}
