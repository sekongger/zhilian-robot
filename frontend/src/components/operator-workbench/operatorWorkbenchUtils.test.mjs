import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getCatalogOperatorBadgeRows,
  getPipelinePreviewDisabledReason,
  readDragPayloadData,
  serializeDragPayload,
} from './operatorWorkbenchUtils.mjs'

test('readDragPayloadData falls back to text/plain payload', () => {
  const payload = { source: 'catalog', operator: 'pdf_source_ingest' }
  const dataTransfer = {
    getData(type) {
      if (type === 'application/json') return ''
      if (type === 'text/plain') return serializeDragPayload(payload)
      return ''
    },
  }

  assert.deepEqual(readDragPayloadData(dataTransfer), payload)
})

test('getPipelinePreviewDisabledReason allows template preview when entry sample exists and all operators implemented', () => {
  const operatorMap = {
    source_record_map: { name: 'source_record_map', status: 'implemented', input_type: 'SourceRecordListDTO' },
    event_enrich: { name: 'event_enrich', status: 'implemented', input_type: 'NormalizedBatchDTO' },
  }

  const reason = getPipelinePreviewDisabledReason({
    currentOperatorNames: ['source_record_map', 'event_enrich'],
    operatorMap,
    previewSample: { inputType: 'SourceRecordListDTO', payload: { records: [] } },
  })

  assert.equal(reason, '')
})

test('getPipelinePreviewDisabledReason blocks pipelines with planned operators', () => {
  const operatorMap = {
    pdf_source_ingest: { name: 'pdf_source_ingest', status: 'implemented', input_type: 'PdfSourceDTO' },
    outline_extract: { name: 'outline_extract', status: 'planned', input_type: 'DocumentDTO' },
  }

  const reason = getPipelinePreviewDisabledReason({
    currentOperatorNames: ['pdf_source_ingest', 'outline_extract'],
    operatorMap,
    previewSample: { inputType: 'PdfSourceDTO', payload: { source_id: '1' } },
  })

  assert.match(reason, /outline_extract/)
  assert.match(reason, /尚未接入可执行实现/)
})

test('getCatalogOperatorBadgeRows keeps state badges separate from IO badges', () => {
  const { stateBadges, ioBadges } = getCatalogOperatorBadgeRows({
    status: 'planned',
    operator_class: 'general',
    stage: 'ingest',
    input_type: 'DocxSourceDTO',
    output_type: 'DocumentSourceDTO',
    applicable_sources: ['report', 'docx', 'extra'],
  })

  assert.deepEqual(
    stateBadges.map((item) => item.label),
    ['规划中', '通用基础', 'ingest'],
  )
  assert.deepEqual(
    ioBadges.map((item) => item.label),
    ['入: DocxSourceDTO', '出: DocumentSourceDTO', 'report', 'docx', '拖拽到中间编排区'],
  )
})
