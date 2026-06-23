const PATH_LABELS = {
  company_to_technology: '布局技术',
  technology_to_company: '技术关联公司',
  company_to_product: '发布产品',
  product_to_company: '产品关联公司',
  company_to_company: '合作伙伴',
  company_to_document: '相关资讯',
  technology_to_document: '相关资讯',
  product_to_document: '相关资讯',
  person_to_document: '相关资讯',
  document_anchor_technology: '文档关联技术',
  document_anchor_product: '文档关联产品',
  document_anchor_company: '文档关联公司',
}

function normalizeText(value) {
  return String(value || '').trim()
}

function inferAnchorFromQuery(query) {
  const text = normalizeText(query)
  const matches = text.match(/[\u4e00-\u9fa5A-Za-z0-9·]{2,24}(?:机器人|科技|智能|公司|集团|股份|平台|系统|机械臂)/g) || []
  return normalizeText(matches[0] || text.slice(0, 12))
}

function relationLabel(pathTag) {
  const tag = normalizeText(pathTag).split('.').slice(-1)[0]
  return PATH_LABELS[tag] || '图谱命中'
}

function nodeStyle(type) {
  if (type === 'anchor') return { color: '#17304a' }
  if (type === 'document') return { color: '#3f6c8f' }
  return { color: '#217346' }
}

export function buildOpenSpgGraphModel({ query, openspgHits, graphPathView }) {
  if (graphPathView?.nodes?.length) {
    return {
      nodes: graphPathView.nodes.map((item) => ({
        id: item.id,
        label: item.label,
        type: item.kind === 'statement' ? 'statement' : item.kind === 'document' ? 'document' : item.kind === 'anchor' ? 'anchor' : 'target',
        rawType: item.type,
      })),
      edges: (graphPathView.edges || []).map((item) => ({
        from: item.from,
        to: item.to,
        label: item.label,
      })),
    }
  }
  const hits = Array.isArray(openspgHits) ? openspgHits : []
  const anchorLabel = normalizeText(hits[0]?.anchor_name) || inferAnchorFromQuery(query)
  if (!anchorLabel || hits.length === 0) {
    return { nodes: [], edges: [] }
  }

  const nodes = [{ id: 'anchor', label: anchorLabel, type: 'anchor', ...nodeStyle('anchor') }]
  const edges = []
  const seenNodeIds = new Set(['anchor'])

  hits.slice(0, 6).forEach((hit, index) => {
    const docTitle = normalizeText(hit.doc_title)
    const targetId = `target:${hit.id || index}`
    const targetLabel = normalizeText(hit.name) || `命中 ${index + 1}`
    if (docTitle) {
      const docId = `doc:${docTitle}`
      if (!seenNodeIds.has(docId)) {
        seenNodeIds.add(docId)
        nodes.push({ id: docId, label: docTitle, type: 'document', ...nodeStyle('document') })
        edges.push({ from: 'anchor', to: docId, label: '关联文档' })
      }
      if (!seenNodeIds.has(targetId)) {
        seenNodeIds.add(targetId)
        nodes.push({ id: targetId, label: targetLabel, type: 'target', ...nodeStyle('target') })
      }
      edges.push({ from: docId, to: targetId, label: relationLabel(hit.path_tag) })
      return
    }

    if (!seenNodeIds.has(targetId)) {
      seenNodeIds.add(targetId)
      nodes.push({ id: targetId, label: targetLabel, type: 'target', ...nodeStyle('target') })
    }
    edges.push({ from: 'anchor', to: targetId, label: relationLabel(hit.path_tag) })
  })

  return { nodes, edges }
}

export function buildTraceOverview(trace) {
  const payload = trace || {}
  const workflow = payload.workflow_reference || {}
  const tables = Array.isArray(payload.tables_used) ? payload.tables_used : []
  const sources = Array.isArray(payload.data_sources) ? payload.data_sources : []
  const runtime = payload.industry_qa || {}
  const queryPlan = payload.query_plan || {}
  const queryFilters = queryPlan.filters || {}
  const reasoningPath = Array.isArray(payload.reasoning_path) ? payload.reasoning_path : []
  const modelUsage = payload.model_usage || {}

  const workflowItems = [
    { label: 'run_id', value: workflow.run_id || '-' },
    { label: '状态', value: workflow.status || '-' },
    { label: '命中事件', value: (workflow.matched_event_ids || []).join(', ') || '-' },
    { label: '命中数量', value: workflow.matched_count ?? '-' },
  ]

  const dataItems = [
    { label: '读取表', value: tables.map((item) => item.table).join(', ') || '-' },
    { label: '读取源', value: sources.map((item) => `${item.name} (${item.stage})`).join(', ') || '-' },
    { label: '写入集合', value: (runtime.collections_written || []).join(', ') || '-' },
    { label: 'session_id', value: runtime.session_id || '-' },
    { label: 'artifact_id', value: queryFilters.artifact_id || '-' },
    { label: 'release_id', value: queryFilters.release_id || '-' },
    { label: 'release_version', value: queryFilters.release_version || '-' },
  ]

  const analysisItems = [
    { label: '查询', value: queryPlan.query || '-' },
    { label: '回答模式', value: queryPlan.answer_mode || '-' },
    { label: '时间窗', value: queryPlan.hours ? `${queryPlan.hours}h` : '-' },
    { label: '模型提供方', value: modelUsage.provider || '-' },
  ]

  return {
    workflowItems,
    dataItems,
    analysisItems,
    analysisSteps: reasoningPath,
  }
}
