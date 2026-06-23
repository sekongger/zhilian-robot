import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const pagePath = path.resolve(__dirname, '../src/pages/PlatformOverviewPage.jsx')

test('knowledge computing panel presents showcase modules instead of runtime drawers', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.match(source, /知识计算/)
  assert.match(source, /产业网大图/)
  assert.match(source, /knowledge_fusion/)
  assert.match(source, /后续接入/)
})

test('knowledge computing panel no longer shows dependency-count oriented runtime copy', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.doesNotMatch(source, /知识图谱模块详情/)
  assert.doesNotMatch(source, /Schema 关系图/)
})
