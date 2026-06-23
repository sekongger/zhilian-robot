import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const appPath = path.resolve(__dirname, '../src/App.jsx')
const openksLayoutPath = path.resolve(__dirname, '../src/components/OpenKSLayout.jsx')
const overviewPath = path.resolve(__dirname, '../src/pages/PlatformOverviewPage.jsx')
const openksPortalPath = path.resolve(__dirname, '../src/utils/openksPortal.js')
const platformPortalPath = path.resolve(__dirname, '../src/utils/platformPortal.js')

test('app registers the openks workbench route', () => {
  const source = fs.readFileSync(appPath, 'utf8')

  assert.match(source, /path="\s*\/openks\s*"/)
  assert.match(source, /path="\s*\/openks\/workbench\s*"/)
  assert.match(source, /OpenKSWorkbenchPage/)
  assert.match(source, /OpenKSLayout/)
})

test('openks uses independent layout and navigation instead of main platform layout', () => {
  const source = fs.readFileSync(openksLayoutPath, 'utf8')

  assert.match(source, /OpenKS 知识计算工作台/)
  assert.match(source, /OpenKS 独立工作台/)
  assert.match(source, /getOpenksPortalUrl/)
  assert.match(source, /主链/)
  assert.doesNotMatch(source, /Build Jobs|任务/)
})

test('platform overview can jump to configured openks portal address', () => {
  const source = fs.readFileSync(overviewPath, 'utf8')

  assert.match(source, /getOpenksPortalUrl/)
  assert.match(source, /openks-portal/)
  assert.match(source, /window\.open/)
  assert.match(source, /'_blank'|" _blank "|"_blank"/)
})

test('portal utils keep independent-domain defaults for openks and main platform', () => {
  const openksSource = fs.readFileSync(openksPortalPath, 'utf8')
  const platformSource = fs.readFileSync(platformPortalPath, 'utf8')

  assert.match(openksSource, /ai-openks\.quant-chi\.com/)
  assert.match(platformSource, /ai-zhilian\.quant-chi\.com/)
})
