import test from 'node:test'
import assert from 'node:assert/strict'

import { buildNewsKgWorkbenchModel } from '../src/pages/workflowWorkbenchModel.mjs'

test('buildNewsKgWorkbenchModel normalizes queue and latest run fields', () => {
  const model = buildNewsKgWorkbenchModel({
    kg_name: 'news_kg',
    queue: { pending: 3, running: 1, failed: 2, completed: 8 },
    latest_run: {
      run_id: 'KGRUN_9',
      status: 'completed',
      processed: 4,
      statements_written: 11,
    },
  })

  assert.equal(model.kgName, 'news_kg')
  assert.equal(model.pending, 3)
  assert.equal(model.running, 1)
  assert.equal(model.failed, 2)
  assert.equal(model.completed, 8)
  assert.equal(model.latestRunId, 'KGRUN_9')
  assert.equal(model.latestRunStatus, 'completed')
  assert.equal(model.latestProcessed, 4)
  assert.equal(model.latestStatementsWritten, 11)
})
