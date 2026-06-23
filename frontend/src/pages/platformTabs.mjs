import { OPENKS_COLLABORATION_STACK } from './openksCatalog.mjs'

export const DEFAULT_PLATFORM_TAB = 'overview'
export const PLATFORM_NAV_MODE = 'header-only'

const TAB_KEY_ALIASES = {
  'data-elements': 'data-hub',
  'agent-apps': 'intelligent-service',
}

export const PLATFORM_TABS = [
  {
    key: 'overview',
    title: '整体概况',
    heroTitle: '产业网链平台整体概况',
    heroSummary: '主任务是先看清五板块如何接力，不在这里执行操作；你会看到整体链路、当前主链和下一步入口。',
    subtitle: '整体思路、架构图和主链导航总览',
    sources: ['architecture', 'platform-overview'],
    highlights: ['主链总览', '板块导航', '资讯先行闭环'],
    activeSummary: '当前查看的是平台总体方案、分层关系和下一步进入哪个工作区。',
  },
  {
    key: 'data-hub',
    title: '数据汇聚',
    heroTitle: '产业数据汇聚中心',
    heroSummary: '主任务是检查资讯和研报资源是否接入、治理是否正常；你会看到资源规模、质量状态和下钻入口。',
    subtitle: '以资源卡片组织资讯、研报等数据资源，承接接入、治理和证据视角',
    docTypes: ['资讯', '研报'],
    sources: ['resource-hub', 'document-pipeline', 'resource-ingestion'],
    highlights: ['主任务: 检查接入', '资源卡片', '治理与质量'],
    activeSummary: '当前查看的是数据资源规模、治理状态，以及应该进入哪个数据工作区继续处理。',
  },
  {
    key: 'knowledge-computing',
    title: '知识计算',
    heroTitle: 'OpenKS知识建模与计算',
    heroSummary: '主任务是运行并管理 `kag_openspg` 主链；你会看到 OpenKS 定义关系、最新 Run / Artifact / Release，以及进入 workflow 的入口。',
    subtitle: '由 supxmind-openks 承接 OpenKS 知识定义层，并通过 KAG/OpenSPG 输出可追踪知识产物',
    projectName: 'supxmind-openks',
    sources: ['openks-catalog', 'model-studio'],
    collaboration: OPENKS_COLLABORATION_STACK,
    highlights: ['主任务: 运行主链', 'Run / Artifact / Release', 'OpenKS -> KAG -> OpenSPG'],
    activeSummary: '当前查看的是 base_kg 与 news_kg 的定义关系、主链运行状态和可追踪执行摘要。',
  },
  {
    key: 'chain-analysis',
    title: '网链分析',
    heroTitle: '产业网链洞察',
    heroSummary: '主任务是基于当前 Artifact 做关系与趋势分析；你会先看到摘要，再进入图谱与热度工作区。',
    subtitle: '围绕关系网络、热度趋势和时序洞察消费知识产物',
    sources: ['graph', 'temporal'],
    highlights: ['主任务: 分析 Artifact', '图谱关系探索', '热点与时序洞察'],
    activeSummary: '当前查看的是知识产物进入分析视角后的摘要与下一步入口。',
  },
  {
    key: 'intelligent-service',
    title: '智能服务',
    heroTitle: '结构化知识服务入口',
    heroSummary: '主任务是基于当前 Release 发起问答与接口消费；你会看到可直接进入产业问答与 Open API 的入口。',
    subtitle: '当前以产业问答智能体和 Open API 为主入口，承接知识消费层',
    sources: ['industry-qa', 'open-api'],
    primaryAgent: '产业问答智能体',
    highlights: ['主任务: 消费 Release', '问答入口', '证据追踪与知识来源'],
    activeSummary: '当前查看的是结构化知识对用户和场景的服务出口与下一步入口。',
  },
]

export function getPlatformTabByKey(key) {
  return PLATFORM_TABS.find((item) => item.key === key) || PLATFORM_TABS[0]
}

export function resolvePlatformTabKey(rawKey) {
  const nextKey = TAB_KEY_ALIASES[rawKey] || rawKey
  return PLATFORM_TABS.some((item) => item.key === nextKey) ? nextKey : DEFAULT_PLATFORM_TAB
}
