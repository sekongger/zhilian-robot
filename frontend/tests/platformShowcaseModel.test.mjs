import test from 'node:test'
import assert from 'node:assert/strict'

import { PLATFORM_SHOWCASE_SECTIONS, getPlatformShowcaseByKey } from '../src/pages/platformShowcaseModel.mjs'

test('platform showcase model exposes five top-level sections in pilot-platform order', () => {
  assert.deepEqual(
    PLATFORM_SHOWCASE_SECTIONS.map((item) => item.key),
    ['overview', 'data-hub', 'knowledge-computing', 'chain-analysis', 'intelligent-service'],
  )
})

test('platform showcase model maps required design modules into each section', () => {
  const overview = getPlatformShowcaseByKey('overview')
  const dataHub = getPlatformShowcaseByKey('data-hub')
  const knowledgeComputing = getPlatformShowcaseByKey('knowledge-computing')
  const chainAnalysis = getPlatformShowcaseByKey('chain-analysis')
  const intelligentService = getPlatformShowcaseByKey('intelligent-service')

  assert.equal(overview.title, '整体概况')
  assert.ok(overview.modules.some((item) => item.title === '平台能力总览'))

  assert.equal(dataHub.title, '数据汇聚')
  assert.ok(dataHub.modules.some((item) => item.title === '数据资源池'))
  assert.ok(dataHub.contracts.some((item) => item.title === 'DataHub 头条资讯接口'))

  assert.equal(knowledgeComputing.title, '知识计算')
  assert.ok(knowledgeComputing.modules.some((item) => item.title === '产业网大图'))
  assert.ok(knowledgeComputing.actions.some((item) => item.label === '进入 OpenKS 工作台'))
  assert.equal(knowledgeComputing.actions[0].target, '/')
  assert.ok(knowledgeComputing.contracts.some((item) => item.title === 'Graphiti 接入契约'))
  assert.ok(knowledgeComputing.governance.some((item) => item.title === 'OpenSPG 主生产链'))

  assert.equal(chainAnalysis.title, '网链分析')
  assert.ok(chainAnalysis.modules.some((item) => item.title === '四链分析'))
  assert.ok(chainAnalysis.governance.some((item) => item.title === '图谱审核与优化'))

  assert.equal(intelligentService.title, '智能服务')
  assert.ok(intelligentService.modules.some((item) => item.title === '头条推送'))
})

test('platform showcase model marks external integration modules as pending access', () => {
  const sections = PLATFORM_SHOWCASE_SECTIONS.flatMap((section) => section.modules)
  const pendingModules = sections.filter((item) => item.integration === 'pending')

  assert.ok(pendingModules.length >= 5)
  assert.ok(pendingModules.every((item) => item.badge === '后续接入'))
})
