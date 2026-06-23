import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildKnowledgeRuntimeDetailModel,
  buildKnowledgeRuntimeCollections,
  buildKnowledgeTabModel,
  buildModuleCapabilityItems,
  buildWorkflowStepItems,
  getModuleReadiness,
} from '../src/pages/platformOverviewModel.mjs'

test('buildKnowledgeTabModel respects declared module status instead of file existence only', () => {
  const model = buildKnowledgeTabModel({
    modules: [
      {
        name: 'news_kg',
        title: '资讯知识库',
        stage: 'fact',
        owner: '楼彦炜',
        status: 'active',
        dependencies: ['base_kg'],
        has_schema: true,
        has_builder: true,
        has_reasoner: true,
        has_solver: true,
        has_tests: true,
      },
    ],
    workflow: { run_id: 'wf_1', status: 'success' },
    newsKg: {
      queue: { pending: 4, running: 1, failed: 0, completed: 6 },
      latest_run: { run_id: 'KGRUN_1', status: 'completed' },
    },
  })

  assert.equal(model.workflow.run_id, 'wf_1')
  assert.equal(model.groups.fact.length, 1)
  assert.equal(model.groups.fact[0].readiness, 'ready')
  assert.equal(model.groups.fact[0].dependencyCount, 1)
  assert.deepEqual(model.groups.fact[0].dependencyLabels, ['base_kg'])
  assert.equal(model.newsKg.queue.pending, 4)
  assert.equal(model.newsKg.latest_run.run_id, 'KGRUN_1')
})

test('getModuleReadiness keeps skeleton modules as skeleton even when files exist', () => {
  assert.equal(getModuleReadiness({
    status: 'skeleton',
    has_schema: true,
    has_builder: true,
    has_reasoner: true,
    has_solver: true,
    has_tests: true,
  }), 'skeleton')
})

test('buildModuleCapabilityItems distinguishes implemented and skeleton capabilities', () => {
  const implemented = buildModuleCapabilityItems({
    name: 'news_kg',
    status: 'active',
    has_schema: true,
    has_builder: true,
    has_reasoner: true,
    has_solver: true,
    has_tests: true,
  })
  const skeleton = buildModuleCapabilityItems({
    name: 'trend',
    status: 'skeleton',
    has_schema: true,
    has_builder: true,
    has_reasoner: true,
    has_solver: true,
    has_tests: true,
  })

  assert.equal(implemented[0].state, 'implemented')
  assert.match(implemented[1].description, /kg_input_queue|真实实现|构建/)
  assert.equal(skeleton[0].state, 'skeleton')
  assert.match(skeleton[0].description, /骨架文件/)
})

test('buildWorkflowStepItems maps workflow statuses into stepper-friendly states', () => {
  const items = buildWorkflowStepItems({
    run_id: 'wf_1',
    step_statuses: {
      model: { status: 'success' },
      collect: { status: 'success' },
      process: { status: 'running' },
      extract: { status: 'idle' },
      execute: { status: 'idle' },
      apply: { status: 'idle' },
    },
  })

  assert.equal(items.length, 6)
  assert.equal(items[0].status, 'finish')
  assert.equal(items[1].status, 'finish')
  assert.equal(items[2].status, 'process')
  assert.equal(items[2].label, '处理中')
  assert.equal(items[5].status, 'wait')
})

test('buildKnowledgeTabModel hides non-traceable modules by default', () => {
  const model = buildKnowledgeTabModel({
    modules: [
      {
        name: 'base_kg',
        title: '产业网链基础',
        stage: 'fact',
        owner: '蔡旭东、陆文韬',
        status: 'active',
        dependencies: [],
        has_schema: true,
        has_builder: true,
        has_reasoner: true,
        has_solver: true,
        has_tests: true,
      },
      {
        name: 'news_kg',
        title: '资讯知识库',
        stage: 'fact',
        owner: '楼彦炜',
        status: 'active',
        dependencies: ['base_kg'],
        has_schema: true,
        has_builder: true,
        has_reasoner: true,
        has_solver: true,
        has_tests: true,
      },
      {
        name: 'report_kg',
        title: '研报知识库',
        stage: 'fact',
        owner: '李奕君',
        status: 'skeleton',
        dependencies: ['base_kg'],
        has_schema: true,
        has_builder: true,
        has_reasoner: true,
        has_solver: true,
        has_tests: true,
      },
    ],
  })

  assert.deepEqual(model.groups.fact.map((item) => item.name), ['base_kg', 'news_kg'])
  assert.equal(model.groups.cognition.length, 0)
  assert.equal(model.groups.decision.length, 0)
})

test('buildKnowledgeRuntimeCollections sorts runs artifacts and releases by created time', () => {
  const collections = buildKnowledgeRuntimeCollections({
    runs: [
      { run_id: 'KRUN_1', created_at: '2026-03-16T10:00:00', artifact_ref: 'KART_1' },
      { run_id: 'KRUN_2', created_at: '2026-03-16T11:00:00', artifact_ref: 'KART_2' },
    ],
    artifacts: [
      { artifact_id: 'KART_1', created_at: '2026-03-16T10:00:10', version: 'news_kg:1' },
      { artifact_id: 'KART_2', created_at: '2026-03-16T11:00:10', version: 'news_kg:2' },
    ],
    releases: [
      { release_id: 'KREL_1', created_at: '2026-03-16T10:05:00', artifact_id: 'KART_1', status: 'active' },
      { release_id: 'KREL_2', created_at: '2026-03-16T11:05:00', artifact_id: 'KART_2', status: 'released' },
    ],
  })

  assert.equal(collections.runs[0].run_id, 'KRUN_2')
  assert.equal(collections.artifacts[0].artifact_id, 'KART_2')
  assert.equal(collections.releases[0].release_id, 'KREL_2')
  assert.equal(collections.latestRelease?.artifact_id, 'KART_2')
  assert.equal(collections.activeRelease?.release_id, 'KREL_1')
})

test('buildKnowledgeRuntimeDetailModel links selected run to artifacts and releases', () => {
  const detail = buildKnowledgeRuntimeDetailModel({
    runs: [
      { run_id: 'KRUN_1', created_at: '2026-03-16T10:00:00', artifact_ref: 'KART_1' },
      { run_id: 'KRUN_2', created_at: '2026-03-16T11:00:00', artifact_ref: 'KART_2' },
    ],
    artifacts: [
      { artifact_id: 'KART_1', run_id: 'KRUN_1', version: 'news_kg:1', created_at: '2026-03-16T10:00:10' },
      { artifact_id: 'KART_2', run_id: 'KRUN_2', version: 'news_kg:2', created_at: '2026-03-16T11:00:10' },
    ],
    releases: [
      { release_id: 'KREL_1', artifact_id: 'KART_1', version: 'rel-001', created_at: '2026-03-16T10:05:00' },
      { release_id: 'KREL_2', artifact_id: 'KART_2', version: 'rel-002', created_at: '2026-03-16T11:05:00' },
    ],
    selectedRunId: 'KRUN_2',
  })

  assert.equal(detail.selectedRun?.run_id, 'KRUN_2')
  assert.deepEqual(detail.runArtifacts.map((item) => item.artifact_id), ['KART_2'])
  assert.equal(detail.selectedArtifact?.artifact_id, 'KART_2')
  assert.deepEqual(detail.artifactReleases.map((item) => item.release_id), ['KREL_2'])
  assert.equal(detail.selectedRelease?.release_id, 'KREL_2')
})
