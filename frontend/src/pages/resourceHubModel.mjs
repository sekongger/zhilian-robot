const RESOURCE_TAB_ORDER = ['数据源', '数据库表设计', '数据接入和治理任务', '数据质量']

export const RESOURCE_METRIC_DEFS = [
  ['raw_documents', '原始'],
  ['resource_documents', '标准'],
  ['entities', '实体'],
  ['statements', '陈述'],
]

export function buildResourceHubModel({ summary = {}, cards = [], detail = null } = {}) {
  const orderedCards = [...cards].sort((left, right) => String(left?.resource_key || '').localeCompare(String(right?.resource_key || '')))
  const detailTabs = RESOURCE_TAB_ORDER.map((label) => ({
    key: label,
    label,
    content: detail?.tabs?.[label] ?? null,
    itemCount: Array.isArray(detail?.tabs?.[label])
      ? detail.tabs[label].length
      : (detail?.tabs?.[label] && typeof detail.tabs[label] === 'object' ? Object.keys(detail.tabs[label]).length : 0),
  }))

  return {
    summary: {
      resources: Number(summary?.resources || 0),
      rawDocuments: Number(summary?.raw_documents || 0),
      resourceDocuments: Number(summary?.resource_documents || 0),
      entities: Number(summary?.entities || 0),
      statements: Number(summary?.statements || 0),
      queuePending: Number(summary?.queue_pending || 0),
      pendingTasks: Number(summary?.pending_tasks || 0),
    },
    cards: orderedCards,
    detailSummary: {
      tabCount: detailTabs.length,
      qualityKeys: detail?.tabs?.['数据质量'] && typeof detail.tabs['数据质量'] === 'object'
        ? Object.keys(detail.tabs['数据质量']).length
        : 0,
      latestLabel: detail?.label || '',
      rawDocuments: Number(detail?.metrics?.raw_documents || 0),
      resourceDocuments: Number(detail?.metrics?.resource_documents || 0),
      entities: Number(detail?.metrics?.entities || 0),
      statements: Number(detail?.metrics?.statements || 0),
    },
    detailTabs,
  }
}
