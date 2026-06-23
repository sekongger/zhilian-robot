import test from 'node:test'
import assert from 'node:assert/strict'

import {
  OPENKS_WORKBENCH_BLOCKS,
  getOpenksWorkbenchBlockByKey,
} from '../src/pages/openksWorkbenchModel.mjs'

test('openks workbench model exposes four production-oriented blocks in display order', () => {
  assert.deepEqual(
    OPENKS_WORKBENCH_BLOCKS.map((item) => item.key),
    ['schema', 'kg-modules', 'production-chain', 'graph-results'],
  )
})

test('openks workbench model keeps schema modules production-chain and results sections', () => {
  const schema = getOpenksWorkbenchBlockByKey('schema')
  const kgModules = getOpenksWorkbenchBlockByKey('kg-modules')
  const productionChain = getOpenksWorkbenchBlockByKey('production-chain')
  const graphResults = getOpenksWorkbenchBlockByKey('graph-results')

  assert.equal(schema.title, 'Schema')
  assert.equal(kgModules.title, 'KG模块')
  assert.equal(productionChain.title, '生产主链')
  assert.equal(graphResults.title, '图谱结果')

  assert.ok(schema.items.length > 0)
  assert.ok(kgModules.items.length > 0)
  assert.ok(productionChain.items.length > 0)
  assert.ok(graphResults.items.length > 0)
})
