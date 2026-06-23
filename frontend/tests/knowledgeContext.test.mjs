import test from 'node:test'
import assert from 'node:assert/strict'

import { parseArtifactContext, parseReleaseContext } from '../src/pages/knowledgeContext.mjs'

test('parseArtifactContext reads artifact id and version from search params', () => {
  const params = new URLSearchParams({
    artifact_id: 'KART_1',
    artifact_version: 'news_kg:20260316',
  })

  const context = parseArtifactContext(params)

  assert.equal(context.artifactId, 'KART_1')
  assert.equal(context.artifactVersion, 'news_kg:20260316')
  assert.equal(context.hasArtifactContext, true)
})

test('parseReleaseContext reads release id and version from search params', () => {
  const params = new URLSearchParams({
    release_id: 'KREL_1',
    release_version: 'rel-001',
  })

  const context = parseReleaseContext(params)

  assert.equal(context.releaseId, 'KREL_1')
  assert.equal(context.releaseVersion, 'rel-001')
  assert.equal(context.hasReleaseContext, true)
})
