import test from 'node:test'
import assert from 'node:assert/strict'

import { buildOpenSpgGraphModel, buildTraceOverview } from '../src/pages/industryQaTraceUtils.mjs'

test('buildOpenSpgGraphModel creates anchor-document-hit graph for multi-hop result', () => {
  const model = buildOpenSpgGraphModel({
    query: '智链机器人布局了哪些技术',
    openspgHits: [
      {
        id: 'TECH_1',
        name: '机器视觉',
        label: 'zhilian.Technology',
        path_tag: 'document_anchor_technology',
        source: 'graph.multi_hop',
        doc_title: '智链机器人联合宇树科技推进具身智能产线落地',
      },
    ],
  })

  assert.equal(model.nodes.length, 3)
  assert.ok(model.nodes.some((item) => item.label === '智链机器人'))
  assert.ok(model.nodes.some((item) => item.label === '智链机器人联合宇树科技推进具身智能产线落地'))
  assert.ok(model.nodes.some((item) => item.label === '机器视觉'))
  assert.equal(model.edges.length, 2)
})

test('buildOpenSpgGraphModel prefers real graph_path_view when available', () => {
  const model = buildOpenSpgGraphModel({
    query: '智链机器人布局了哪些技术',
    graphPathView: {
      mode: 'statement_path',
      nodes: [
        { id: 'n1', label: '智链机器人', kind: 'anchor', type: 'Company' },
        { id: 'n2', label: '研发技术', kind: 'statement', type: 'Statement' },
        { id: 'n3', label: '机器视觉', kind: 'entity', type: 'Technology' },
        { id: 'n4', label: '智链机器人联合宇树科技推进具身智能产线落地', kind: 'document', type: 'Document' },
      ],
      edges: [
        { from: 'n1', to: 'n2', label: '主体' },
        { from: 'n2', to: 'n3', label: '研发技术' },
        { from: 'n2', to: 'n4', label: '证据文档' },
      ],
    },
    openspgHits: [],
  })

  assert.equal(model.nodes.length, 4)
  assert.ok(model.nodes.some((item) => item.label === '研发技术'))
  assert.equal(model.edges.length, 3)
})

test('buildTraceOverview groups workflow, tables and reasoning into structured sections', () => {
  const overview = buildTraceOverview({
    query_plan: { query: '智链机器人布局了哪些技术', answer_mode: 'openspg', top_k: 5, hours: 168 },
    workflow_reference: { run_id: 'wf_demo', status: 'success', matched_event_ids: ['evt_1'], matched_count: 1 },
    tables_used: [{ table: 'crawled_articles', role: 'workflow_headline_source' }],
    data_sources: [{ name: 'openspg', stage: 'graph_reason_search' }],
    industry_qa: { session_id: 'qa_s_demo', message_id: 'qa_m_demo', collections_written: ['qa_messages', 'qa_traces'] },
    reasoning_path: ['workflow:apply', 'semantic:openspg.multi_hop', 'gateway:open-api'],
    model_usage: { mode: 'openspg', provider: 'openspg-first' },
  })

  assert.equal(overview.workflowItems[0].label, 'run_id')
  assert.equal(overview.dataItems[0].label, '读取表')
  assert.equal(overview.analysisItems[0].label, '查询')
  assert.ok(overview.analysisSteps.includes('semantic:openspg.multi_hop'))
})
