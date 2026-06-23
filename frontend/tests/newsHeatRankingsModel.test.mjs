import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ENTITY_HEAT_TYPE_OPTIONS,
  buildHeatRankingQueryParams,
  buildFormulaRows,
  formatHeatScore,
  normalizeRankingResponse,
} from '../src/pages/newsHeatRankingsModel.mjs'

test('news heat ranking model exposes expected entity type tabs', () => {
  assert.deepEqual(
    ENTITY_HEAT_TYPE_OPTIONS.map((item) => item.value),
    ['Enterprise', 'Product', 'Person', 'Technology', 'Region'],
  )
  assert.equal(ENTITY_HEAT_TYPE_OPTIONS[0].label, '公司')
})

test('formatHeatScore keeps two decimals and handles missing values', () => {
  assert.equal(formatHeatScore(86.236), '86.24')
  assert.equal(formatHeatScore(null), '0.00')
})

test('buildFormulaRows renders explainable formula weights', () => {
  const rows = buildFormulaRows({
    mention_weight: 0.45,
    news_hotness_weight: 0.2,
    source_weight: 0.15,
    freshness_weight: 0.1,
    anchor_weight: 0.1,
  })

  assert.equal(rows[0].name, '提及强度')
  assert.equal(rows[0].weightText, '45%')
  assert.equal(rows[4].name, '锚点可信度')
})

test('normalizeRankingResponse preserves ranking evidence and defaults formula version', () => {
  const normalized = normalizeRankingResponse({
    period_type: 'daily',
    entity_type: 'Enterprise',
    items: [
      {
        rank: 1,
        entity_name: '腾讯',
        heat_score: 98,
        top_evidence: [{ title: '腾讯资讯', url: 'https://36kr.com/p/1' }],
      },
    ],
  })

  assert.equal(normalized.formula_version, 'entity_heat_v1')
  assert.equal(normalized.items[0].top_evidence[0].url, 'https://36kr.com/p/1')
})

test('buildHeatRankingQueryParams omits date to request latest snapshot', () => {
  const params = buildHeatRankingQueryParams({
    periodType: 'weekly',
    entityType: 'Enterprise',
    date: null,
    limit: 50,
  })

  assert.deepEqual(params, {
    period_type: 'weekly',
    entity_type: 'Enterprise',
    limit: 50,
  })
})

test('buildHeatRankingQueryParams formats selected date when provided', () => {
  const params = buildHeatRankingQueryParams({
    periodType: 'daily',
    entityType: 'Product',
    date: { format: () => '2026-06-18' },
    limit: 20,
  })

  assert.deepEqual(params, {
    period_type: 'daily',
    date: '2026-06-18',
    entity_type: 'Product',
    limit: 20,
  })
})
