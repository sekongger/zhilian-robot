export const PLATFORM_OVERVIEW_MODE = 'hub'

const STAGE_KEY_ALIASES = {
  'data-elements': 'data-hub',
  'agent-apps': 'intelligent-service',
}

export const PLATFORM_STAGE_HUBS = {
  overview: {
    contentMode: 'summary',
    visualType: 'architecture',
    eyebrow: 'Stage 00',
    heading: '平台整体概况',
    summary: '主任务是先看清五板块关系和当前主链，不在这里直接执行操作。',
    shortcuts: [
      { label: '进入数据汇聚', path: '/platform?tab=data-hub', type: 'primary' },
      { label: '进入OpenKS知识建模与计算', path: '/platform?tab=knowledge-computing', type: 'default' },
      { label: '进入智能服务', path: '/platform?tab=intelligent-service', type: 'default' },
    ],
    spotlights: [
      {
        title: '主任务',
        value: '选择下一板块',
        description: '先看清链路分工，再进入数据汇聚、知识计算、分析或智能服务工作区。',
      },
      {
        title: '你会看到什么',
        value: '整体链路与主链',
        description: '这里展示平台闭环、资讯先行策略，以及当前以 kag_openspg 为主链的建设重点。',
      },
      {
        title: '下一步去哪',
        value: '进入具体工作区',
        description: '用快捷入口进入对应板块，而不是在整体概况页停留做操作。',
      },
    ],
    facts: [
      '整体概况页只负责说明架构和实施路径，不承载具体操作。',
      '页面会明确五板块之间的上下游关系。',
      '资讯是当前第一条完成闭环的数据类型。',
    ],
    flowNarrative: [
      {
        title: '数据汇聚',
        description: '先把 RSS、爬虫和人工导入的资讯接进来，完成资源归集、去重、治理和质量检查。',
      },
      {
        title: 'OpenKS知识建模与计算',
        description: '再由 news_kg 消费治理后的资讯，把文档转换成实体、关系、陈述和图谱结构。',
      },
      {
        title: '网链分析',
        description: '分析层统一消费结构化产物，查看关系网络、热度变化、时序演进和异常信号。',
      },
      {
        title: '智能服务',
        description: '最后把结构化知识交给问答和 Open API，对外输出可追溯的答案与能力。',
      },
    ],
  },
  'data-hub': {
    contentMode: 'summary',
    visualType: 'resource-hub',
    eyebrow: 'Stage 01',
    heading: '数据汇聚工作区',
    summary: '主任务是检查资讯、研报资源是否已经接入并完成治理。',
    shortcuts: [
      { label: '进入数据管理', path: '/data', type: 'primary' },
      { label: '查看证据联查', path: '/data-evidence', type: 'default' },
      { label: '进入文档处理中心', path: '/legacy/document-pipeline', type: 'default' },
    ],
    resourceTabs: ['数据源', '数据库表设计', '数据接入和治理任务', '数据质量'],
    spotlights: [
      {
        title: '主任务',
        value: '检查接入与治理',
        description: '先确认资讯、研报的资源规模、治理任务和质量状态是否正常。',
      },
      {
        title: '你会看到什么',
        value: '总览 + 资源卡片',
        description: '顶部是整体指标，下方用资源卡片进入各类资源的详细状态。',
      },
      {
        title: '下一步去哪',
        value: '进入数据管理',
        description: '确认状态后，进入 `/data` 或证据联查继续处理具体资源问题。',
      },
    ],
    facts: [
      '数据汇聚页强调资源视角，而不是抽象的数据要素命名。',
      '资源卡片下钻后会展示数据源、库表、治理任务和质量四个 Tab。',
      '证据联查仍用于按 trace_id / statement_id / doc_id 回溯来源证据。',
    ],
  },
  'knowledge-computing': {
    contentMode: 'summary',
    visualType: 'workflow-status',
    eyebrow: 'Stage 02',
    heading: 'OpenKS知识建模与计算工作区',
    summary: '主任务是运行并管理 `kag_openspg` 主链，把 OpenKS 定义稳定转成可消费知识产物。',
    repoName: 'supxmind-openks',
    repoPath: 'supxmind/supxmind-openks',
    shortcuts: [
      { label: '进入工作流页', path: '/workflow', type: 'primary' },
      { label: '进入模型管理', path: '/model-studio', type: 'default' },
    ],
    spotlights: [
      {
        title: '主任务',
        value: '运行 kag_openspg 主链',
        description: '从 OpenKS schema、KAG bridge 到 OpenSPG 图物化，再回收 Run / Artifact / Release。',
      },
      {
        title: '你会看到什么',
        value: '定义 + 运行时对象',
        description: '当前页面展示 base_kg、news_kg 的定义关系，以及最新 Run / Artifact / Release 状态。',
      },
      {
        title: '下一步去哪',
        value: '进入 workflow',
        description: '主入口是 `/workflow`，模型管理页仅保留给高级联调和调试。',
      },
    ],
    groupSummary: [
      { title: '事实类 KG', description: 'news / report / enterprise / policy / patent 等' },
      { title: '认知类 KG', description: 'industry_chain / supply_chain / innovation_chain / capital_chain' },
      { title: '决策类 KG', description: 'hotspot / trend / risk_alert / recommendation 等' },
    ],
  },
  'chain-analysis': {
    contentMode: 'summary',
    visualType: 'graph-headlines',
    eyebrow: 'Stage 03',
    heading: '网链分析工作区',
    summary: '主任务是基于当前 Artifact 查看关系网络、热度和时序变化。',
    shortcuts: [
      { label: '进入图谱分析', path: '/graph', type: 'primary' },
      { label: '进入热度页', path: '/temporal', type: 'default' },
    ],
    spotlights: [
      {
        title: '主任务',
        value: '分析当前 Artifact',
        description: '这里承接知识产物的分析消费，优先查看某个 Artifact 对应的网链关系与趋势。',
      },
      {
        title: '你会看到什么',
        value: '关系图 + 热度趋势',
        description: '先看摘要，再进入图谱分析或热度页做进一步探索。',
      },
      {
        title: '下一步去哪',
        value: '进入图谱分析',
        description: '主入口是 `/graph`，优先带上 artifact_id 继续深挖具体知识产物。',
      },
    ],
    facts: [
      '图谱分析和热度分析都是成熟功能，适合作为独立工作区。',
      '首页先交代当前主题的节点、关系和趋势，再引导进入独立分析页。',
    ],
  },
  'intelligent-service': {
    contentMode: 'summary',
    visualType: 'headlines-qa',
    eyebrow: 'Stage 04',
    heading: '智能服务工作区',
    summary: '主任务是基于当前 Release 发起问答和接口消费，把知识交付给用户与应用。',
    shortcuts: [
      { label: '进入产业问答智能体', path: '/agent/industry-qa', type: 'primary' },
      { label: '进入 Open API 联调', path: '/applications', type: 'default' },
    ],
    spotlights: [
      {
        title: '主任务',
        value: '消费当前 Release',
        description: '优先基于已激活 Release 发起问答或联调 Open API，而不是直接查看底层构建细节。',
      },
      {
        title: '你会看到什么',
        value: '问答入口 + Open API',
        description: '这里展示当前主应用、可消费的样本，以及进入问答与联调的入口。',
      },
      {
        title: '下一步去哪',
        value: '进入产业问答',
        description: '主入口是 `/agent/industry-qa`，并优先带上 release_id / release_version 上下文。',
      },
    ],
    facts: [
      '首页只展示应用定位和入口，不直接嵌入会话面板。',
      '当前智能体应用的主消费对象仍是产业问答和后续 Open API 接入。',
    ],
  },
}

export function getStageHub(key) {
  const normalizedKey = STAGE_KEY_ALIASES[key] || key
  return PLATFORM_STAGE_HUBS[normalizedKey] || PLATFORM_STAGE_HUBS.overview
}
