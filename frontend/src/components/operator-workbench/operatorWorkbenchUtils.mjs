export const serializeDragPayload = (payload) => JSON.stringify(payload)

export const readDragPayloadData = (dataTransfer) => {
  if (!dataTransfer) return null
  const rawPayload =
    dataTransfer.getData('application/json') ||
    dataTransfer.getData('text/plain') ||
    dataTransfer.getData('text')

  if (!rawPayload) return null

  try {
    return JSON.parse(rawPayload)
  } catch (error) {
    return null
  }
}

export const getPipelinePreviewDisabledReason = ({
  currentOperatorNames = [],
  operatorMap = {},
  previewSample = null,
}) => {
  if (!currentOperatorNames.length) {
    return '请先拖入至少一个算子。'
  }

  const firstOperatorName = currentOperatorNames[0]
  const firstOperator = firstOperatorName ? operatorMap[firstOperatorName] : null

  if (!previewSample) {
    return firstOperator?.input_type
      ? `当前仅支持 MarkdownSourceDTO / PdfSourceDTO / WebPageSourceDTO / SourceRecordListDTO 作为试跑入口，暂未提供 ${firstOperator.input_type} 的样例输入。`
      : '当前链路缺少入口算子。'
  }

  const unimplementedOperators = currentOperatorNames.filter((operatorName) => {
    const operator = operatorMap[operatorName]
    return operator && operator.status !== 'implemented'
  })

  if (unimplementedOperators.length > 0) {
    return `以下算子尚未接入可执行实现，当前无法试跑：${unimplementedOperators.join('、')}`
  }

  return ''
}

export const getCatalogOperatorBadgeRows = (operator = {}) => {
  const stateBadges = [
    {
      key: 'status',
      color: operator.status === 'implemented' ? 'green' : 'gold',
      label: operator.status === 'implemented' ? '已实现' : '规划中',
    },
    {
      key: 'class',
      color: operator.operator_class === 'business' ? 'volcano' : 'blue',
      label: operator.operator_class === 'business' ? '业务扩展' : '通用基础',
    },
    {
      key: 'stage',
      color: 'processing',
      label: operator.stage || '',
    },
  ].filter((item) => item.label)

  const ioBadges = [
    {
      key: 'input',
      color: 'geekblue',
      label: `入: ${operator.input_type || '-'}`,
    },
    {
      key: 'output',
      color: 'cyan',
      label: `出: ${operator.output_type || '-'}`,
    },
    ...((operator.applicable_sources || []).slice(0, 2).map((source) => ({
      key: `source:${source}`,
      color: 'default',
      label: source,
    })) || []),
    {
      key: 'hint',
      color: 'purple',
      label: '拖拽到中间编排区',
    },
  ]

  return {
    stateBadges,
    ioBadges,
  }
}
