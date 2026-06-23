import test from 'node:test'
import assert from 'node:assert/strict'

import { buildResourceHubModel } from '../src/pages/resourceHubModel.mjs'

test('buildResourceHubModel normalizes summary and keeps detail tabs ordered', () => {
  const model = buildResourceHubModel({
    summary: {
      resources: 2,
      raw_documents: 100,
      resource_documents: 80,
      entities: 30,
      statements: 50,
      queue_pending: 7,
      pending_tasks: 4,
    },
    cards: [
      { resource_key: 'report', label: '研报' },
      { resource_key: 'news', label: '资讯' },
    ],
    detail: {
      tabs: {
        数据质量: { duplicate_rate: 0.1 },
        数据源: [{ name: 'RSS' }],
        数据接入和治理任务: [{ name: 'build_news_kg_queue' }],
        数据库表设计: [{ name: 'raw_documents' }],
      },
    },
  })

  assert.equal(model.summary.queuePending, 7)
  assert.equal(model.cards[0].resource_key, 'news')
  assert.deepEqual(model.detailTabs.map((item) => item.label), ['数据源', '数据库表设计', '数据接入和治理任务', '数据质量'])
  assert.equal(model.detailTabs[0].content[0].name, 'RSS')
  assert.equal(model.detailTabs[0].itemCount, 1)
  assert.equal(model.detailTabs[1].itemCount, 1)
  assert.equal(model.detailSummary.tabCount, 4)
  assert.equal(model.detailSummary.qualityKeys, 1)
})
