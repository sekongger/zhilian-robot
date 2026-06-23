import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildMomentumPreview,
  pickGraphPreviewCompany,
} from '../src/pages/platformOverviewAnalytics.mjs'

test('pickGraphPreviewCompany prefers the first company from headlines', () => {
  const company = pickGraphPreviewCompany([
    { headline_title: '机器人产业链观察', companies: [] },
    { headline_title: '华为与ABB推进产线升级', companies: ['华为', 'ABB'] },
  ])

  assert.equal(company, '华为')
})

test('buildMomentumPreview keeps top five entities and formats percentage', () => {
  const preview = buildMomentumPreview([
    { name: '华为', current_momentum: 0.62 },
    { name: 'ABB', current_momentum: 0.58 },
    { name: '特斯拉', current_momentum: 0.54 },
    { name: '小米', current_momentum: 0.48 },
    { name: '宇树科技', current_momentum: 0.42 },
    { name: '优必选', current_momentum: 0.35 },
  ])

  assert.equal(preview.length, 5)
  assert.deepEqual(preview[0], { name: '华为', percentage: 62 })
  assert.equal(preview[4].name, '宇树科技')
})
