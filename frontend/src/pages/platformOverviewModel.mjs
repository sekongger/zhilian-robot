const stageOrder = ['fact', 'cognition', 'decision']
const traceableModuleNames = new Set(['base_kg', 'news_kg'])
const workflowStepOrder = ['model', 'collect', 'process', 'extract', 'execute', 'apply']
const workflowStepTitle = {
  model: '建模',
  collect: '采集',
  process: '处理',
  extract: '抽取',
  execute: '执行',
  apply: '应用',
}

const capabilityDefs = [
  ['schema', 'Schema'],
  ['builder', 'Builder'],
  ['reasoner', 'Reasoner'],
  ['solver', 'Solver'],
  ['tests', 'Tests'],
]

const capabilityDescriptions = {
  base_kg: {
    schema: '定义产业网链基础实体和统一 ID 规则骨架。',
    builder: '提供基础透传构建逻辑，作为上层 KG 的公共起点。',
    reasoner: '提供基础透传推理占位，供后续扩展复用。',
    solver: '提供基础查询壳，当前不返回业务结果。',
    tests: '已有基础结构与运行契约测试。',
  },
  news_kg: {
    schema: '定义资讯文档、企业、技术、产品、事件等核心结构。',
    builder: '消费 kg_input_queue，写入 entity_instances、inc_statement、inc_context 和图谱。',
    reasoner: '基于同文实体共现补充共现关系推理。',
    solver: '从 news_kg 结构化陈述中按关键词做检索返回。',
    tests: '已覆盖 builder 与 solver 的最小回归测试。',
  },
}

function normalizeWorkflowStepStatus(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'success' || normalized === 'partial_success' || normalized === 'skipped') {
    return { status: 'finish', label: '已完成' }
  }
  if (normalized === 'running' || normalized === 'queued') {
    return { status: 'process', label: '处理中' }
  }
  if (normalized === 'failed') {
    return { status: 'error', label: '失败' }
  }
  return { status: 'wait', label: '待开始' }
}

export function getModuleReadiness(module) {
  const status = String(module?.status || '').toLowerCase()
  if (status === 'active' || status === 'implemented') return 'ready'
  if (status === 'partial') return 'partial'
  if (status === 'skeleton') return 'skeleton'
  if (status === 'planned' || status === 'empty') return 'empty'

  const completed = [
    module?.has_schema,
    module?.has_builder,
    module?.has_reasoner,
    module?.has_solver,
    module?.has_tests,
  ].filter(Boolean).length

  if (completed >= 5) return 'ready'
  if (completed >= 2) return 'partial'
  if (completed >= 1 || module?.status === 'skeleton') return 'skeleton'
  return 'empty'
}

export function buildModuleCapabilityItems(module = {}) {
  const isImplemented = getModuleReadiness(module) === 'ready'
  return capabilityDefs.map(([key, label]) => {
    const exists = Boolean(module?.[`has_${key}`])
    const state = !exists ? 'pending' : isImplemented ? 'implemented' : 'skeleton'
    const defaultDescription = state === 'implemented'
      ? `${label} 已接入当前模块的真实实现。`
      : state === 'skeleton'
      ? `${label} 目前只有骨架文件，业务逻辑待实现。`
      : `${label} 尚未创建。`

    return {
      key,
      label,
      state,
      description: capabilityDescriptions[module?.name]?.[key] || defaultDescription,
    }
  })
}

export function buildKnowledgeTabModel({ modules = [], workflow = null, newsKg = null }) {
  const groups = {
    fact: [],
    cognition: [],
    decision: [],
  }

  for (const module of modules) {
    if (!traceableModuleNames.has(module?.name)) continue
    const stage = module?.stage || module?.groupKey
    if (!groups[stage]) continue
    groups[stage].push({
      ...module,
      dependencyCount: Array.isArray(module?.dependencies) ? module.dependencies.length : 0,
      dependencyLabels: Array.isArray(module?.dependencies) ? module.dependencies : [],
      readiness: getModuleReadiness(module),
    })
  }

  for (const stage of stageOrder) {
    groups[stage].sort((left, right) => String(left?.name || '').localeCompare(String(right?.name || '')))
  }

  return {
    workflow: workflow || {},
    newsKg: newsKg || { queue: {}, latest_run: {} },
    groups,
  }
}

export function buildKnowledgeRuntimeCollections({ runs = [], artifacts = [], releases = [] } = {}) {
  const byCreatedAtDesc = (left, right) => String(right?.created_at || '').localeCompare(String(left?.created_at || ''))
  const normalizedRuns = [...runs].sort(byCreatedAtDesc)
  const normalizedArtifacts = [...artifacts].sort(byCreatedAtDesc)
  const normalizedReleases = [...releases].sort(byCreatedAtDesc)

  return {
    runs: normalizedRuns,
    artifacts: normalizedArtifacts,
    releases: normalizedReleases,
    latestRun: normalizedRuns[0] || null,
    latestArtifact: normalizedArtifacts[0] || null,
    latestRelease: normalizedReleases[0] || null,
    activeRelease: normalizedReleases.find((item) => String(item?.status || '').toLowerCase() === 'active') || null,
  }
}

export function buildKnowledgeRuntimeDetailModel({
  runs = [],
  artifacts = [],
  releases = [],
  selectedRunId = '',
  selectedArtifactId = '',
} = {}) {
  const collections = buildKnowledgeRuntimeCollections({ runs, artifacts, releases })
  const selectedRun = collections.runs.find((item) => item.run_id === selectedRunId) || collections.latestRun || null
  const runArtifacts = selectedRun
    ? collections.artifacts.filter((item) => item.run_id === selectedRun.run_id || item.artifact_id === selectedRun.artifact_ref)
    : []
  const selectedArtifact = runArtifacts.find((item) => item.artifact_id === selectedArtifactId) || runArtifacts[0] || collections.latestArtifact || null
  const artifactReleases = selectedArtifact
    ? collections.releases.filter((item) => item.artifact_id === selectedArtifact.artifact_id)
    : []
  const selectedRelease = artifactReleases[0] || collections.latestRelease || null

  return {
    ...collections,
    selectedRun,
    runArtifacts,
    selectedArtifact,
    artifactReleases,
    selectedRelease,
  }
}

export function buildWorkflowStepItems(workflow = {}) {
  return workflowStepOrder.map((key) => {
    const statusInfo = normalizeWorkflowStepStatus(workflow?.step_statuses?.[key]?.status)
    return {
      key,
      title: workflowStepTitle[key],
      status: statusInfo.status,
      label: statusInfo.label,
    }
  })
}
