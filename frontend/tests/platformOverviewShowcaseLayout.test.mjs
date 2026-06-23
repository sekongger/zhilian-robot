import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const pagePath = path.resolve(__dirname, '../src/pages/PlatformOverviewPage.jsx')

test('platform overview page renders showcase structure for section hero modules and placeholders', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.match(source, /platform-showcase-shell/)
  assert.match(source, /platform-showcase-section-head/)
  assert.match(source, /platform-showcase-module-grid/)
  assert.match(source, /platform-showcase-placeholder-badge/)
})

test('platform overview page keeps the five pilot-platform section names visible in code', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.match(source, /整体概况/)
  assert.match(source, /数据汇聚/)
  assert.match(source, /知识计算/)
  assert.match(source, /网链分析/)
  assert.match(source, /智能服务/)
})
