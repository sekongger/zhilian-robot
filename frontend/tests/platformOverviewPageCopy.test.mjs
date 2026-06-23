import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const pagePath = path.resolve(__dirname, '../src/pages/PlatformOverviewPage.jsx')

test('platform overview page removes duplicate stage-map navigation from body', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.doesNotMatch(source, /<StageMap\s+activeKey=/)
})

test('platform overview page contains pilot-platform showcase copy instead of runtime-only copy', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.match(source, /后续接入/)
  assert.match(source, /数据资源池/)
  assert.match(source, /产业网大图/)
  assert.match(source, /四链分析/)
  assert.match(source, /头条推送/)
  assert.match(source, /接口定义与规范/)
  assert.match(source, /链路状态与审核/)
  assert.match(source, /独立域名/)
  assert.doesNotMatch(source, /当前为中试平台前台展示页，后台系统先以“后续接入”形式占位。/)
})
