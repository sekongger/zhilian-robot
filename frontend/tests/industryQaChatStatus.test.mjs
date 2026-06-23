import test from 'node:test'
import assert from 'node:assert/strict'

import { buildAssistantPlaceholder } from '../src/pages/industryQaChatStatus.mjs'

test('buildAssistantPlaceholder returns readable text for stream stages', () => {
  assert.equal(buildAssistantPlaceholder('processing'), '正在创建问答任务…')
  assert.equal(buildAssistantPlaceholder('retrieving'), '正在检索 workflow / 图谱数据…')
  assert.equal(buildAssistantPlaceholder('answering'), '正在生成回答…')
})
