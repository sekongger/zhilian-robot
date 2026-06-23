import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const pagePath = path.resolve(__dirname, '../src/pages/OpenKSWorkbenchPage.jsx')
const servicePath = path.resolve(__dirname, '../src/services/openksWorkbenchApi.js')

test('openks workbench page binds to real api service instead of static-only blocks', () => {
  const source = fs.readFileSync(pagePath, 'utf8')

  assert.match(source, /openksWorkbenchApi/)
  assert.match(source, /useEffect/)
  assert.match(source, /getOverview/)
  assert.match(source, /getWorkflowLatest/)
  assert.match(source, /runWorkflowModel/)
  assert.match(source, /runWorkflowExtract/)
  assert.match(source, /runWorkflowExecute/)
  assert.match(source, /getWorkflowStepDetail/)
  assert.match(source, /getRuntimeRuns/)
  assert.match(source, /getRuntimeArtifacts/)
  assert.match(source, /getRuntimeReleases/)
  assert.match(source, /Schema 概览|KG 模块状态|图谱结果|生产主链/)
  assert.match(source, /DataHub 接口规范|Graphiti 接入说明|OpenSPG 主生产链|图谱审核|主链步骤|执行 Schema Sync|执行 Extract|执行 Execute|Step Detail/)
  assert.doesNotMatch(source, /Build Jobs|最新构建任务/)
})

test('openks workbench api exposes production-chain and runtime requests', () => {
  const source = fs.readFileSync(servicePath, 'utf8')

  assert.match(source, /getOverview/)
  assert.match(source, /getModules/)
  assert.match(source, /getWorkflowLatest/)
  assert.match(source, /runWorkflowModel/)
  assert.match(source, /runWorkflowExtract/)
  assert.match(source, /runWorkflowExecute/)
  assert.match(source, /getWorkflowStepDetail/)
  assert.match(source, /getRuntimeRuns/)
  assert.match(source, /getRuntimeArtifacts/)
  assert.match(source, /getRuntimeReleases/)
  assert.doesNotMatch(source, /getBuildJobs/)
})
