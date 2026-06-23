import React, { useMemo, useState } from 'react'
import { Alert, Button, Card, Descriptions, Empty, Segmented, Space, Spin, Tag, Typography } from 'antd'
import {
  ArrowDownOutlined,
  ApartmentOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  NodeIndexOutlined,
  PlusOutlined,
  RetweetOutlined,
} from '@ant-design/icons'
import { readDragPayloadData, serializeDragPayload } from './operatorWorkbenchUtils.mjs'

const { Paragraph, Text } = Typography

const DropZone = ({ onDropPayload, label = '拖到这里', active = false }) => (
  <div
    onDragOver={(event) => {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'move'
    }}
    onDrop={(event) => {
      event.preventDefault()
      event.stopPropagation()
      const payload = readDragPayloadData(event.dataTransfer)
      if (payload) {
        onDropPayload?.(payload)
      }
    }}
    style={{
      borderRadius: 12,
      border: `1px dashed ${active ? '#1c7ed6' : '#b8c7d6'}`,
      padding: '10px 12px',
      background: active ? 'rgba(28, 126, 214, 0.08)' : 'rgba(248, 251, 255, 0.85)',
      color: '#52607a',
      textAlign: 'center',
      fontSize: 12,
    }}
  >
    <Space>
      <PlusOutlined />
      <span>{label}</span>
    </Space>
  </div>
)

const OperatorPipelineCanvas = ({
  mode = 'template',
  pipelines = [],
  currentNodes = [],
  customNodes = [],
  operatorMap = {},
  selectedPipelineKey,
  onSelectPipeline,
  selectedOperatorName,
  onSelectOperator,
  onAppendOperator,
  onInsertOperator,
  onReorderOperator,
  onRemoveOperator,
  onClearCustomPipeline,
  onLoadTemplateIntoCustom,
  validationResult,
  validating = false,
  onExecutePreview,
  previewRunning = false,
  previewResult = null,
  previewDisabledReason = '',
  headerActions = null,
}) => {
  const [activeDropIndex, setActiveDropIndex] = useState(null)
  const currentPipeline = pipelines.find((item) => item.key === selectedPipelineKey) || pipelines[0]
  const pipelineOptions = pipelines.map((item) => ({
    label: item.name,
    value: item.key,
  }))

  const issuesByIndex = useMemo(() => {
    if (mode !== 'custom') {
      return new Map()
    }
    const issueMap = new Map()
    ;(validationResult?.issues || []).forEach((issue) => {
      if (typeof issue.index !== 'number') return
      const list = issueMap.get(issue.index) || []
      list.push(issue)
      issueMap.set(issue.index, list)
    })
    return issueMap
  }, [validationResult])

  const handleDrop = (payload, index) => {
    if (!payload) return
    setActiveDropIndex(null)
    if (payload.source === 'catalog') {
      if (typeof index === 'number') {
        onInsertOperator?.(payload.operator, index)
      } else {
        onAppendOperator?.(payload.operator)
      }
      return
    }
    if (payload.source === 'canvas' && typeof payload.index === 'number') {
      const nextIndex = typeof index === 'number' ? index : currentNodes.length
      onReorderOperator?.(payload.index, nextIndex)
    }
  }

  const renderIssueSummary = () => {
    if (mode !== 'custom') return null
    if (!validationResult && !validating) {
      return (
        <Alert
          type="info"
          showIcon
          message="开始自定义编排"
          description="把左侧算子拖进来，系统会自动检查相邻算子的输入输出 DTO 是否匹配。"
        />
      )
    }

    if (validating) {
      return (
        <Alert
          type="info"
          showIcon
          message="正在校验当前 pipeline"
          description={<Spin size="small" />}
        />
      )
    }

    if (validationResult?.valid) {
      return (
        <Alert
          type="success"
          showIcon
          message="当前 pipeline 契约校验通过"
          description={`警告 ${validationResult?.summary?.warning_count || 0} 条，可继续优化但不阻断编排。`}
        />
      )
    }

    return (
      <Alert
        type="error"
        showIcon
        message="当前 pipeline 存在契约问题"
        description={
          <Space direction="vertical" size={4}>
            {(validationResult?.issues || []).slice(0, 4).map((issue, index) => (
              <Text key={`${issue.code}-${index}`} style={{ color: '#7a2e2e' }}>
                [{issue.code}] {issue.message}
              </Text>
            ))}
          </Space>
        }
      />
    )
  }

  const renderPreviewSummary = () => {
    if (!previewResult) return null

    if (previewResult.valid === false) {
      return (
        <Alert
          type="error"
          showIcon
          message="执行预览失败"
          description={
            <Space direction="vertical" size={4}>
              {(previewResult.issues || []).map((issue, index) => (
                <Text key={`${issue.code}-${index}`} style={{ color: '#7a2e2e' }}>
                  [{issue.code}] {issue.message}
                </Text>
              ))}
            </Space>
          }
        />
      )
    }

    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Alert
          type="success"
          showIcon
          message="执行预览成功"
          description={`共执行 ${previewResult.steps?.length || 0} 个算子，最终输出 ${previewResult.final_output_type || '-'}`}
        />
        <Descriptions
          size="small"
          column={1}
          bordered
          items={[
            {
              key: 'finalType',
              label: '最终输出',
              children: previewResult.final_output_type || '-',
            },
            {
              key: 'finalSummary',
              label: '输出摘要',
              children:
                Object.entries(previewResult.final_output_summary || {})
                  .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : value}`)
                  .join(' | ') || '-',
            },
          ]}
        />
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12,
          }}
        >
          {(previewResult.steps || []).map((step, index) => (
            <div
              key={`${step.operator}-${index}`}
              style={{
                borderRadius: 12,
                border: '1px solid #d7e0ea',
                background: '#f8fbff',
                padding: 12,
              }}
            >
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Space>
                  <Tag color="processing">Step {index + 1}</Tag>
                  <Text strong>{step.operator}</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {step.input_type} -&gt; {step.output_type}
                </Text>
                {Object.entries(step.summary || {}).map(([key, value]) => (
                  <Text key={key} style={{ fontSize: 12, color: '#52607a' }}>
                    {key}: {Array.isArray(value) ? value.join(', ') : String(value)}
                  </Text>
                ))}
              </Space>
            </div>
          ))}
        </div>
      </Space>
    )
  }

  if (mode === 'template' && !currentPipeline) {
    return (
      <Card title="链路排布">
        <Empty description="暂无预置链路" />
      </Card>
    )
  }

  const title = mode === 'custom' ? '自定义编排' : '链路排布'

  return (
    <Card
      title={title}
      extra={headerActions || (
        mode === 'template' ? (
          <Space wrap size={[6, 6]}>
            <Segmented
              size="small"
              options={pipelineOptions}
              value={currentPipeline?.key}
              onChange={onSelectPipeline}
            />
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={previewRunning}
              disabled={Boolean(previewDisabledReason)}
              onClick={onExecutePreview}
              title={previewDisabledReason || '执行预览'}
            >
              执行预览
            </Button>
          </Space>
        ) : (
          <Space wrap size={[6, 6]}>
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={previewRunning}
              disabled={Boolean(previewDisabledReason)}
              onClick={onExecutePreview}
              title={previewDisabledReason || '执行预览'}
            >
              执行预览
            </Button>
            <Button size="small" onClick={onLoadTemplateIntoCustom} icon={<RetweetOutlined />}>
              从模板载入
            </Button>
            <Button size="small" danger onClick={onClearCustomPipeline} icon={<DeleteOutlined />}>
              清空
            </Button>
          </Space>
        )
      )}
      styles={{ body: { padding: 16 } }}
    >
      <Space
        direction="vertical"
        size={16}
        style={{ width: '100%' }}
        onDragOver={(event) => {
          event.preventDefault()
          event.dataTransfer.dropEffect = 'copy'
        }}
        onDrop={(event) => {
          event.preventDefault()
          const payload = readDragPayloadData(event.dataTransfer)
          if (payload) {
            handleDrop(payload)
          }
        }}
      >
        {previewDisabledReason ? (
          <Alert
            type="warning"
            showIcon
            message="当前链路暂不支持试跑"
            description={previewDisabledReason}
          />
        ) : null}

        {mode === 'template' ? (
          <div
            style={{
              borderRadius: 14,
              padding: 16,
              background: 'linear-gradient(135deg, rgba(11, 110, 153, 0.08) 0%, rgba(28, 126, 214, 0.04) 100%)',
              border: '1px solid rgba(28, 126, 214, 0.14)',
            }}
          >
            <Space direction="vertical" size={8}>
              <Space>
                <ApartmentOutlined style={{ color: '#0b6e99' }} />
                <Text strong style={{ fontSize: 16, color: '#14213d' }}>
                  {currentPipeline?.name}
                </Text>
                <Tag color="blue">{currentPipeline?.source_types?.join(' / ')}</Tag>
              </Space>
              <Paragraph style={{ marginBottom: 0, color: '#52607a' }}>
                {currentPipeline?.description}
              </Paragraph>
            </Space>
          </div>
        ) : (
          <>
            {renderIssueSummary()}
            <Alert
              type="info"
              showIcon
              message="拖拽规则"
              description="左侧卡片可拖入这里；已有卡片也可以继续拖动换位。系统会按相邻算子的输入/输出 DTO 自动提示错误和警告。"
            />
            {renderPreviewSummary()}
          </>
        )}

        {mode === 'template' ? (
          <>
            {renderPreviewSummary()}
            <DropZone
              label="把左侧算子拖到这里，立即切换到自定义模式开始编排"
              onDropPayload={(payload) => handleDrop(payload)}
            />
          </>
        ) : null}

        {mode === 'custom' && currentNodes.length === 0 ? (
          <DropZone
            active={activeDropIndex === 0}
            label="拖动左侧算子到这里开始构建 pipeline"
            onDropPayload={(payload) => handleDrop(payload, 0)}
          />
        ) : null}

        <div
          onDragOver={(event) => {
            event.preventDefault()
            event.dataTransfer.dropEffect = 'move'
          }}
          onDrop={(event) => {
            event.preventDefault()
            const payload = readDragPayloadData(event.dataTransfer)
            if (payload) {
              handleDrop(payload)
            }
          }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12,
            alignItems: 'stretch',
          }}
        >
          {currentNodes.map((node, index) => {
            const operator = operatorMap[node.operator]
            const selected = node.operator === selectedOperatorName
            const nodeIssues = issuesByIndex.get(index) || []
            const hasError = nodeIssues.some((issue) => issue.severity === 'error')
            const hasWarning = nodeIssues.some((issue) => issue.severity === 'warning')

            return (
              <React.Fragment key={node.key}>
                {mode === 'custom' ? (
                  <div
                    style={{ gridColumn: '1 / -1' }}
                    onDragEnter={() => setActiveDropIndex(index)}
                    onDragLeave={() => setActiveDropIndex((current) => (current === index ? null : current))}
                  >
                    <DropZone
                      active={activeDropIndex === index}
                      label={`插入到第 ${index + 1} 个位置之前`}
                      onDropPayload={(payload) => handleDrop(payload, index)}
                    />
                  </div>
                ) : null}

                <div
                  draggable={mode === 'custom'}
                  onDragOver={(event) => {
                    event.preventDefault()
                    event.dataTransfer.dropEffect = mode === 'custom' ? 'move' : 'copy'
                  }}
                  onDrop={(event) => {
                    event.preventDefault()
                    event.stopPropagation()
                    const payload = readDragPayloadData(event.dataTransfer)
                    if (payload) {
                      handleDrop(payload, index + 1)
                    }
                  }}
                  onDragStart={(event) => {
                    if (mode !== 'custom') return
                    const payload = serializeDragPayload({ source: 'canvas', index, operator: node.operator })
                    event.dataTransfer.effectAllowed = 'move'
                    event.dataTransfer.setData('application/json', payload)
                    event.dataTransfer.setData('text/plain', payload)
                  }}
                  onClick={() => onSelectOperator?.(node.operator)}
                  style={{
                    cursor: 'pointer',
                    minHeight: 184,
                    borderRadius: 16,
                    padding: 16,
                    background: selected
                      ? 'linear-gradient(180deg, rgba(28, 126, 214, 0.14) 0%, rgba(28, 126, 214, 0.05) 100%)'
                      : '#ffffff',
                    border: hasError
                      ? '1px solid #d94841'
                      : hasWarning
                        ? '1px solid #d48806'
                        : selected
                          ? '1px solid #1c7ed6'
                          : '1px solid #d7e0ea',
                    boxShadow: selected ? '0 12px 26px rgba(28, 126, 214, 0.16)' : '0 8px 22px rgba(15, 40, 65, 0.05)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                  }}
                >
                  <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Tag color="processing" style={{ marginInlineEnd: 0 }}>
                      Step {index + 1}
                    </Tag>
                    <Space size={6}>
                      {mode === 'custom' ? (
                        <Button
                          size="small"
                          danger
                          type="text"
                          icon={<DeleteOutlined />}
                          onClick={(event) => {
                            event.stopPropagation()
                            onRemoveOperator?.(index)
                          }}
                        />
                      ) : null}
                      <NodeIndexOutlined style={{ color: '#0b6e99' }} />
                    </Space>
                  </Space>

                  <div>
                    <Text strong style={{ fontSize: 15, color: '#14213d' }}>
                      {node.title}
                    </Text>
                    <div style={{ color: '#52607a', fontSize: 12, marginTop: 4 }}>
                      {node.operator}
                    </div>
                  </div>

                  <Paragraph ellipsis={{ rows: 3 }} style={{ marginBottom: 0, color: '#52607a', minHeight: 64 }}>
                    {operator?.description || '当前节点尚未挂载算子说明。'}
                  </Paragraph>

                  <Space wrap size={[6, 6]}>
                    <Tag color={operator?.status === 'implemented' ? 'green' : 'gold'}>
                      {operator?.status === 'implemented' ? '已实现' : '规划中'}
                    </Tag>
                    <Tag>{operator?.layer || '-'}</Tag>
                    <Tag color="geekblue">入: {operator?.input_type || '-'}</Tag>
                    <Tag color="cyan">出: {operator?.output_type || '-'}</Tag>
                    {hasError ? <Tag color="error">存在错误</Tag> : null}
                    {!hasError && hasWarning ? <Tag color="warning">有警告</Tag> : null}
                  </Space>

                  {mode === 'custom' && nodeIssues.length > 0 ? (
                    <div
                      style={{
                        borderRadius: 10,
                        background: hasError ? 'rgba(217, 72, 65, 0.08)' : 'rgba(212, 136, 6, 0.08)',
                        border: hasError ? '1px solid rgba(217, 72, 65, 0.2)' : '1px solid rgba(212, 136, 6, 0.2)',
                        padding: '10px 12px',
                      }}
                    >
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {nodeIssues.slice(0, 2).map((issue, issueIndex) => (
                          <Text
                            key={`${issue.code}-${issueIndex}`}
                            style={{
                              fontSize: 12,
                              color: hasError ? '#9f2a22' : '#8a5300',
                              lineHeight: 1.5,
                            }}
                          >
                            [{issue.code}] {issue.message}
                          </Text>
                        ))}
                      </Space>
                    </div>
                  ) : null}
                </div>

                {mode === 'template' && index < currentNodes.length - 1 ? (
                  <div
                    aria-hidden="true"
                    style={{
                      gridColumn: '1 / -1',
                      display: 'flex',
                      justifyContent: 'center',
                      marginTop: -2,
                      marginBottom: -2,
                    }}
                  >
                    <ArrowDownOutlined style={{ color: '#8aa2b2', fontSize: 18 }} />
                  </div>
                ) : null}
              </React.Fragment>
            )
          })}

          {mode === 'custom' && currentNodes.length > 0 ? (
            <div
              style={{ gridColumn: '1 / -1' }}
              onDragEnter={() => setActiveDropIndex(currentNodes.length)}
              onDragLeave={() => setActiveDropIndex((current) => (current === currentNodes.length ? null : current))}
            >
              <DropZone
                active={activeDropIndex === currentNodes.length}
                label="拖到这里追加到末尾"
                onDropPayload={(payload) => handleDrop(payload, currentNodes.length)}
              />
            </div>
          ) : null}
        </div>
      </Space>
    </Card>
  )
}

export default OperatorPipelineCanvas
