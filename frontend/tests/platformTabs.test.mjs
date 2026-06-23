import test from 'node:test'
import assert from 'node:assert/strict'

import { PLATFORM_NAV_MODE, PLATFORM_TABS, getPlatformTabByKey, resolvePlatformTabKey } from '../src/pages/platformTabs.mjs'

test('platform tabs expose five linked stages in required order', () => {
  assert.deepEqual(
    PLATFORM_TABS.map((item) => item.key),
    ['overview', 'data-hub', 'knowledge-computing', 'chain-analysis', 'intelligent-service'],
  )
})

test('platform tabs map legacy capabilities into the new chain', () => {
  const overview = getPlatformTabByKey('overview')
  const dataHub = getPlatformTabByKey('data-hub')
  const knowledgeComputing = getPlatformTabByKey('knowledge-computing')
  const chainAnalysis = getPlatformTabByKey('chain-analysis')
  const intelligentService = getPlatformTabByKey('intelligent-service')

  assert.equal(overview.title, '整体概况')
  assert.ok(overview.highlights.includes('主链总览'))

  assert.equal(dataHub.title, '数据汇聚')
  assert.deepEqual(dataHub.docTypes, ['资讯', '研报'])
  assert.ok(dataHub.sources.includes('resource-hub'))
  assert.ok(dataHub.highlights.includes('主任务: 检查接入'))

  assert.equal(knowledgeComputing.title, '知识计算')
  assert.equal(knowledgeComputing.projectName, 'supxmind-openks')
  assert.ok(knowledgeComputing.sources.includes('openks-catalog'))
  assert.deepEqual(knowledgeComputing.collaboration, ['OpenKS', 'KAG', 'OpenSPG'])
  assert.ok(knowledgeComputing.highlights.includes('主任务: 运行主链'))

  assert.ok(chainAnalysis.sources.includes('graph'))
  assert.ok(chainAnalysis.sources.includes('temporal'))
  assert.ok(chainAnalysis.highlights.includes('主任务: 分析 Artifact'))

  assert.ok(intelligentService.sources.includes('industry-qa'))
  assert.equal(intelligentService.primaryAgent, '产业问答智能体')
  assert.ok(intelligentService.highlights.includes('主任务: 消费 Release'))
})

test('platform overview keeps stage switching in the sticky header only', () => {
  assert.equal(PLATFORM_NAV_MODE, 'header-only')
})

test('each platform tab defines a user-facing hero title', () => {
  const overview = getPlatformTabByKey('overview')
  const dataHub = getPlatformTabByKey('data-hub')
  const knowledgeComputing = getPlatformTabByKey('knowledge-computing')
  const chainAnalysis = getPlatformTabByKey('chain-analysis')

  assert.ok(overview.heroTitle)
  assert.ok(dataHub.heroTitle)
  assert.ok(knowledgeComputing.heroTitle)
  assert.ok(chainAnalysis.heroTitle)
  assert.notEqual(dataHub.heroTitle, chainAnalysis.heroTitle)
})

test('platform tabs preserve legacy aliases for migrated stage keys', () => {
  assert.equal(resolvePlatformTabKey('data-elements'), 'data-hub')
  assert.equal(resolvePlatformTabKey('agent-apps'), 'intelligent-service')
  assert.equal(resolvePlatformTabKey('overview'), 'overview')
})
