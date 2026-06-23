import test from 'node:test'
import assert from 'node:assert/strict'

import {
  OPENKS_DEFINITION_LAYERS,
  OPENKS_ENGINE_STACK,
  OPENKS_KG_GROUPS,
  OPENKS_TRACEABLE_MODULES,
  OPENKS_REPO_BLUEPRINT,
  filterTraceableDefinitionLayers,
  filterTraceableOpenksModules,
  flattenOpenksModules,
} from '../src/pages/openksCatalog.mjs'

test('openks catalog lists fact cognition and decision groups', () => {
  assert.deepEqual(OPENKS_KG_GROUPS.map((group) => group.key), ['fact', 'cognition', 'decision'])
})

test('openks blueprint includes common kg cross entry and tests trunks', () => {
  assert.deepEqual(
    OPENKS_REPO_BLUEPRINT,
    ['common', 'kg', 'cross', 'entry', 'tests', 'docs', 'openks.yaml'],
  )
})

test('openks module list includes owners and core chain modules', () => {
  const modules = flattenOpenksModules()
  const moduleNames = modules.map((item) => item.name)
  assert.ok(moduleNames.includes('base_kg'))
  assert.ok(moduleNames.includes('news_kg'))
  assert.ok(moduleNames.includes('report_kg'))
  assert.ok(moduleNames.includes('industry_chain'))

  const news = modules.find((item) => item.name === 'news_kg')
  assert.equal(news.owner, '楼彦炜')
  assert.equal(news.groupKey, 'fact')
})

test('openks catalog keeps OpenKS above KAG and OpenSPG', () => {
  assert.deepEqual(OPENKS_ENGINE_STACK, ['OpenKS', 'KAG', 'OpenSPG'])
  assert.equal(OPENKS_DEFINITION_LAYERS[0].name, 'base_kg')
  assert.equal(OPENKS_DEFINITION_LAYERS[0].title, '基础概念词典')
  assert.equal(OPENKS_DEFINITION_LAYERS[1].title, '网状事实图谱')
  assert.equal(OPENKS_DEFINITION_LAYERS[2].title, '链式认知图谱')
  assert.ok(OPENKS_DEFINITION_LAYERS[1].members.includes('news_kg'))
})

test('openks cognition modules use 图谱库 naming and technology foresight owners are updated', () => {
  const cognitionTitles = OPENKS_KG_GROUPS
    .find((group) => group.key === 'cognition')
    .modules
    .map((item) => item.title)

  assert.ok(cognitionTitles.every((title) => title.endsWith('图谱库')))

  const foresight = flattenOpenksModules().find((item) => item.name === 'technology_foresight')
  assert.equal(foresight.owner, '林辉、徐梓毓')
})

test('openks traceable scope keeps only current in-plan modules', () => {
  assert.deepEqual(OPENKS_TRACEABLE_MODULES, ['base_kg', 'news_kg'])

  const traceableModules = filterTraceableOpenksModules(flattenOpenksModules())
  assert.deepEqual(traceableModules.map((item) => item.name), ['base_kg', 'news_kg'])

  const definitionLayers = filterTraceableDefinitionLayers()
  assert.deepEqual(definitionLayers.map((item) => item.name), ['base_kg', 'element_kgs'])
  assert.deepEqual(definitionLayers[1].members, ['news_kg'])
})
