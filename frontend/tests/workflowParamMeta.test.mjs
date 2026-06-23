import test from 'node:test'
import assert from 'node:assert/strict'

import { ADVANCED_PARAM_KEYS, PARAM_META } from '../src/components/workflow/workflowParamMeta.mjs'

test('workflow param meta exposes chinese labels and default hints', () => {
  assert.equal(PARAM_META.hours_ago.label, '时间范围')
  assert.equal(PARAM_META.max_entries_per_feed.label, '单源采集上限')
  assert.equal(PARAM_META.bridge_limit.label, '处理上限')
  assert.equal(PARAM_META.headlines_top_n.label, '输出条数')
  assert.equal(PARAM_META.project_id.defaultValue, 1)
  assert.equal(PARAM_META.builder_command.advanced, true)
  assert.match(PARAM_META.runtime_profile.help, /固定使用 kag_openspg 主链/)
  assert.match(PARAM_META.apply_schema.help, /OpenKS 编译出的当前 Schema/)
})

test('advanced param keys only include project and builder overrides', () => {
  assert.deepEqual(ADVANCED_PARAM_KEYS, ['project_id', 'builder_command'])
})
