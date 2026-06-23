import test from 'node:test'
import assert from 'node:assert/strict'

import { buildGraphQuickTags, pickInitialArtifactCompany } from '../src/pages/graphPageModel.mjs'

test('buildGraphQuickTags prefers artifact-scoped companies when available', () => {
  const tags = buildGraphQuickTags({
    artifactContext: { hasArtifactContext: true },
    availableCompanies: ['智链机器人', '华为'],
  })

  assert.deepEqual(tags, ['智链机器人', '华为'])
})

test('buildGraphQuickTags falls back to default hot companies when artifact companies absent', () => {
  const tags = buildGraphQuickTags({
    artifactContext: { hasArtifactContext: false },
    availableCompanies: [],
  })

  assert.deepEqual(tags, ['华为', '特斯拉', '小米', 'ABB'])
})

test('pickInitialArtifactCompany uses first artifact company when no explicit name exists', () => {
  const company = pickInitialArtifactCompany({
    artifactContext: { hasArtifactContext: true },
    availableCompanies: ['智链机器人', '华为'],
    searchName: '',
  })

  assert.equal(company, '智链机器人')
})

test('pickInitialArtifactCompany keeps explicit search name over artifact suggestions', () => {
  const company = pickInitialArtifactCompany({
    artifactContext: { hasArtifactContext: true },
    availableCompanies: ['智链机器人', '华为'],
    searchName: '华为',
  })

  assert.equal(company, '华为')
})
