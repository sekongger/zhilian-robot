import assert from 'node:assert/strict'
import test from 'node:test'

import { applyCatalogDrop, buildCustomNode, moveNode } from './pipelineBuilderUtils.mjs'

const operatorMap = {
  pdf_source_ingest: {
    description: '接入本地或对象存储中的 PDF 文件，统一转成文档源记录。',
  },
  pdf_parse: {
    description: '把 PDF 文档解析成正文、页码和版面信息。',
  },
  document_clean: {
    description: '清理噪声字符、页眉页脚和多余空白，生成可抽取正文。',
  },
}

test('buildCustomNode derives title and lane', () => {
  const node = buildCustomNode('pdf_source_ingest', operatorMap, 0)
  assert.equal(node.operator, 'pdf_source_ingest')
  assert.equal(node.lane, 0)
  assert.equal(node.title, '接入本地或对象存储中的 PDF 文件')
})

test('applyCatalogDrop appends operator to empty custom pipeline', () => {
  const nodes = applyCatalogDrop({
    operatorName: 'pdf_source_ingest',
    operatorMap,
    currentNodes: [],
  })

  assert.equal(nodes.length, 1)
  assert.equal(nodes[0].operator, 'pdf_source_ingest')
  assert.equal(nodes[0].lane, 0)
})

test('applyCatalogDrop inserts operator at requested index and relanes nodes', () => {
  const existing = [
    buildCustomNode('pdf_source_ingest', operatorMap, 0),
    buildCustomNode('document_clean', operatorMap, 1),
  ]

  const nodes = applyCatalogDrop({
    operatorName: 'pdf_parse',
    operatorMap,
    currentNodes: existing,
    index: 1,
  })

  assert.deepEqual(
    nodes.map((item) => [item.operator, item.lane]),
    [
      ['pdf_source_ingest', 0],
      ['pdf_parse', 1],
      ['document_clean', 2],
    ],
  )
})

test('moveNode reorders custom nodes', () => {
  const existing = [
    buildCustomNode('pdf_source_ingest', operatorMap, 0),
    buildCustomNode('pdf_parse', operatorMap, 1),
    buildCustomNode('document_clean', operatorMap, 2),
  ]

  const nodes = moveNode(existing, 0, 3)

  assert.deepEqual(
    nodes.map((item) => [item.operator, item.lane]),
    [
      ['pdf_parse', 0],
      ['document_clean', 1],
      ['pdf_source_ingest', 2],
    ],
  )
})
