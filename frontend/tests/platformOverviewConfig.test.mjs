import test from 'node:test'
import assert from 'node:assert/strict'

import {
  PLATFORM_OVERVIEW_MODE,
  PLATFORM_STAGE_HUBS,
  getStageHub,
} from '../src/pages/platformOverviewConfig.mjs'

test('platform overview uses hub layout instead of embedded workspaces', () => {
  assert.equal(PLATFORM_OVERVIEW_MODE, 'hub')
  assert.equal(getStageHub('overview').contentMode, 'summary')
  assert.equal(getStageHub('data-hub').contentMode, 'summary')
  assert.equal(getStageHub('chain-analysis').contentMode, 'summary')
  assert.equal(getStageHub('intelligent-service').contentMode, 'summary')
})

test('data hub stage exposes business-oriented shortcuts', () => {
  const hub = getStageHub('data-hub')
  const labels = hub.shortcuts.map((item) => item.label)

  assert.deepEqual(labels, ['进入数据管理', '查看证据联查', '进入文档处理中心'])
  assert.ok(hub.resourceTabs.includes('数据源'))
  assert.ok(hub.resourceTabs.includes('数据质量'))
})

test('knowledge computing stage summarizes openks instead of rendering module tabs', () => {
  const hub = PLATFORM_STAGE_HUBS['knowledge-computing']
  assert.equal(hub.repoName, 'supxmind-openks')
  assert.equal(hub.groupSummary.length, 3)
  assert.equal(hub.shortcuts[0].path, '/workflow')
  assert.match(hub.spotlights[0].value, /kag_openspg 主链/)
})

test('each stage hub defines a concrete live view instead of card-only copy', () => {
  assert.equal(getStageHub('overview').visualType, 'architecture')
  assert.equal(getStageHub('data-hub').visualType, 'resource-hub')
  assert.equal(getStageHub('knowledge-computing').visualType, 'workflow-status')
  assert.equal(getStageHub('chain-analysis').visualType, 'graph-headlines')
  assert.equal(getStageHub('intelligent-service').visualType, 'headlines-qa')
})

test('stage hub keeps aliases for legacy stage keys', () => {
  assert.equal(getStageHub('data-elements').heading, getStageHub('data-hub').heading)
  assert.equal(getStageHub('agent-apps').heading, getStageHub('intelligent-service').heading)
})

test('overview stage defines a business-facing workflow narrative', () => {
  const overview = getStageHub('overview')

  assert.ok(Array.isArray(overview.flowNarrative))
  assert.equal(overview.flowNarrative.length, 4)
  assert.match(overview.flowNarrative[0].title, /数据汇聚/)
  assert.match(overview.flowNarrative[1].description, /知识计算|news_kg/)
})
