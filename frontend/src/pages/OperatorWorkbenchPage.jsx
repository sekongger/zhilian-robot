import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Card,
  Col,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  message,
} from 'antd'
import {
  ApartmentOutlined,
  CloudUploadOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  ShareAltOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import operatorWorkbenchApi from '../services/operatorWorkbenchApi'
import OperatorCatalogPanel from '../components/operator-workbench/OperatorCatalogPanel'
import OperatorPipelineCanvas from '../components/operator-workbench/OperatorPipelineCanvas'
import PublishedPipelinePanel from '../components/operator-workbench/PublishedPipelinePanel'
import { applyCatalogDrop, moveNode } from '../components/operator-workbench/pipelineBuilderUtils.mjs'
import { getPipelinePreviewDisabledReason } from '../components/operator-workbench/operatorWorkbenchUtils.mjs'
import { getAuth } from '../utils/auth'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const PREVIEW_SAMPLES = {
  MarkdownSourceDTO: {
    inputType: 'MarkdownSourceDTO',
    payload: {
      source_id: 'markdown_preview_001',
      source_type: 'markdown',
      location: 'inline://sample.md',
      title: '机器人企业融资快讯',
      source_name: '工作台样例',
      markdown_text:
        '# 上海某某机器人科技有限公司完成B轮融资\n\n2026年3月，上海某某机器人科技有限公司宣布完成B轮融资，投资方为某产业基金，融资将用于高端装备研发。',
      metadata: {
        category: 'news',
      },
    },
  },
  PdfSourceDTO: {
    inputType: 'PdfSourceDTO',
    payload: {
      source_id: 'pdf_preview_001',
      source_type: 'pdf',
      location: '/tmp/sample-report.pdf',
      title: '高端装备行业深度报告',
      source_name: '工作台样例',
      page_hint: 1,
      metadata: {
        category: 'report',
      },
    },
  },
  WebPageSourceDTO: {
    inputType: 'WebPageSourceDTO',
    payload: {
      source_id: 'web_preview_001',
      source_type: 'webpage',
      location: 'https://example.com/news/robotics-financing',
      title: '网页资讯样例',
      source_name: '工作台样例',
      url: 'https://example.com/news/robotics-financing',
      fetched_at: '2026-04-10T09:00:00',
      metadata: {
        category: 'news',
      },
    },
  },
  SourceRecordListDTO: {
    inputType: 'SourceRecordListDTO',
    payload: {
      records: [
        {
          source_system: 'operator-workbench',
          source_table: 'preview_news',
          record_id: 'record_001',
          record_type: 'document',
          payload: {
            doc_type: 'news',
            title: '机器人企业融资快讯',
            content:
              '上海某某机器人科技有限公司宣布完成B轮融资，投资方为某产业基金，本轮资金用于高端装备研发和产线扩张。',
            source_name: '工作台样例',
            source_type: 'news',
          },
        },
      ],
    },
  },
}

const clonePipelineNodes = (nodes = [], prefix = 'custom') =>
  nodes.map((node, index) => ({
    ...node,
    key: `${prefix}-${index}-${node.operator}`,
    lane: index,
  }))

const OperatorWorkbenchPage = () => {
  const [loading, setLoading] = useState(false)
  const [overview, setOverview] = useState(null)
  const [publishedPipelines, setPublishedPipelines] = useState([])
  const [searchValue, setSearchValue] = useState('')
  const [selectedOperatorName, setSelectedOperatorName] = useState('')
  const [customNodes, setCustomNodes] = useState([])
  const [validationResult, setValidationResult] = useState(null)
  const [validating, setValidating] = useState(false)
  const [previewRunning, setPreviewRunning] = useState(false)
  const [previewResult, setPreviewResult] = useState(null)
  const [selectedPublishedPipelineKey, setSelectedPublishedPipelineKey] = useState('')
  const [publishModalOpen, setPublishModalOpen] = useState(false)
  const [publishSubmitting, setPublishSubmitting] = useState(false)
  const [publishForm] = Form.useForm()

  const loadOverview = async () => {
    setLoading(true)
    try {
      const data = await operatorWorkbenchApi.getOverview()
      setOverview(data || null)
      const published = Array.isArray(data?.published_pipelines) ? data.published_pipelines : []
      setPublishedPipelines(published)
      const firstPublished = published[0]
      const firstOperator = (Array.isArray(data?.operators) ? data.operators : [])[0]
      setSelectedPublishedPipelineKey((current) => current || firstPublished?.key || '')
      setSelectedOperatorName((current) => current || firstOperator?.name || '')
      setValidationResult(null)
      setPreviewResult(null)
    } catch (error) {
      message.error(`读取知识计算工作台失败: ${error.message}`)
      setOverview(null)
      setPublishedPipelines([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  const operators = Array.isArray(overview?.operators) ? overview.operators : []
  const layers = Array.isArray(overview?.layers) ? overview.layers : []
  const businessOperatorCount = operators.filter((operator) => operator.operator_class === 'business').length

  const filteredOperators = useMemo(() => {
    const keyword = searchValue.trim().toLowerCase()
    if (!keyword) return operators
    return operators.filter((operator) => {
      const haystack = [
        operator.name,
        operator.stage,
        operator.description,
        ...(operator.tags || []),
        ...(operator.applicable_sources || []),
      ]
        .join(' ')
        .toLowerCase()
      return haystack.includes(keyword)
    })
  }, [operators, searchValue])

  const operatorMap = useMemo(
    () => Object.fromEntries(operators.map((operator) => [operator.name, operator])),
    [operators],
  )

  const implementedCount = operators.filter((operator) => operator.status === 'implemented').length
  const plannedCount = operators.filter((operator) => operator.status === 'planned').length
  const currentOperatorNames = customNodes.map((node) => node.operator).filter(Boolean)
  const firstOperator = currentOperatorNames[0] ? operatorMap[currentOperatorNames[0]] : null
  const previewSample = firstOperator?.input_type ? PREVIEW_SAMPLES[firstOperator.input_type] || null : null

  const previewDisabledReason = useMemo(
    () =>
      getPipelinePreviewDisabledReason({
        currentOperatorNames,
        operatorMap,
        previewSample,
      }),
    [currentOperatorNames, operatorMap, previewSample],
  )

  const canPublish = useMemo(() => {
    if (!customNodes.length) return false
    if (!validationResult?.valid) return false
    const issues = validationResult?.issues || []
    return !issues.some((issue) => issue.severity === 'error' || ['PLANNED_OPERATOR', 'PIPELINE_NOT_TERMINATED'].includes(issue.code))
  }, [customNodes, validationResult])

  useEffect(() => {
    if (selectedOperatorName || !filteredOperators[0]) return
    setSelectedOperatorName(filteredOperators[0].name)
  }, [filteredOperators, selectedOperatorName])

  useEffect(() => {
    let ignore = false

    const runValidation = async () => {
      setValidating(true)
      try {
        const result = await operatorWorkbenchApi.validatePipeline(customNodes.map((node) => node.operator))
        if (!ignore) {
          setValidationResult(result)
        }
      } catch (error) {
        if (!ignore) {
          setValidationResult({
            valid: false,
            issues: [
              {
                code: 'VALIDATION_REQUEST_FAILED',
                severity: 'error',
                message: error.message,
              },
            ],
            summary: { error_count: 1, warning_count: 0 },
          })
        }
      } finally {
        if (!ignore) {
          setValidating(false)
        }
      }
    }

    runValidation()
    return () => {
      ignore = true
    }
  }, [customNodes])

  useEffect(() => {
    setPreviewResult(null)
  }, [customNodes])

  const appendOperatorToCustom = (operatorName) => {
    setCustomNodes((current) =>
      applyCatalogDrop({
        operatorName,
        operatorMap,
        currentNodes: current,
      }),
    )
    setSelectedOperatorName(operatorName)
  }

  const insertOperatorToCustom = (operatorName, index) => {
    setCustomNodes((current) =>
      applyCatalogDrop({
        operatorName,
        operatorMap,
        currentNodes: current,
        index,
      }),
    )
    setSelectedOperatorName(operatorName)
  }

  const reorderCustomOperator = (fromIndex, toIndex) => {
    setCustomNodes((current) => moveNode(current, fromIndex, toIndex))
  }

  const removeCustomOperator = (index) => {
    setCustomNodes((current) =>
      current
        .filter((_, itemIndex) => itemIndex !== index)
        .map((node, itemIndex) => ({
          ...node,
          lane: itemIndex,
        })),
    )
  }

  const clearCustomPipeline = () => {
    setCustomNodes([])
    setValidationResult(null)
    setPreviewResult(null)
  }

  const loadPublishedPipeline = (pipeline) => {
    const nextNodes = clonePipelineNodes(pipeline?.nodes || [], `published-${pipeline?.key || 'pipeline'}`)
    setCustomNodes(nextNodes)
    setSelectedPublishedPipelineKey(pipeline?.key || '')
    if (nextNodes[0]?.operator) {
      setSelectedOperatorName(nextNodes[0].operator)
    }
    setPreviewResult(null)
  }

  const executePreview = async () => {
    if (previewDisabledReason || !previewSample) return

    setPreviewRunning(true)
    try {
      const result = await operatorWorkbenchApi.executePreview({
        operators: currentOperatorNames,
        input_type: previewSample.inputType,
        input_payload: previewSample.payload,
      })
      setPreviewResult(result)
      if (result.valid) {
        message.success(`执行预览成功，共完成 ${result.steps?.length || 0} 个算子步骤。`)
      } else {
        message.warning('执行预览返回了问题，请查看步骤摘要和错误信息。')
      }
    } catch (error) {
      setPreviewResult({
        valid: false,
        issues: [
          {
            code: 'PREVIEW_REQUEST_FAILED',
            severity: 'error',
            message: error.message,
          },
        ],
        steps: [],
        final_output_type: null,
        final_output_summary: {},
      })
      message.error(`执行预览失败: ${error.message}`)
    } finally {
      setPreviewRunning(false)
    }
  }

  const openPublishModal = () => {
    publishForm.setFieldsValue({
      name: '',
      description: '',
      source_types: Array.from(
        new Set((customNodes || []).flatMap((node) => operatorMap[node.operator]?.applicable_sources || [])),
      )
        .slice(0, 3)
        .join(', '),
    })
    setPublishModalOpen(true)
  }

  const handlePublish = async () => {
    try {
      const values = await publishForm.validateFields()
      const auth = getAuth()
      setPublishSubmitting(true)
      const payload = {
        name: values.name,
        description: values.description || '',
        source_types:
          typeof values.source_types === 'string'
            ? values.source_types
                .split(/[，,]/)
                .map((item) => item.trim())
                .filter(Boolean)
            : [],
        published_by: auth?.user || 'admin',
        nodes: customNodes.map((node, index) => ({
          key: node.key,
          operator: node.operator,
          title: node.title,
          lane: index,
        })),
      }
      const published = await operatorWorkbenchApi.publishPipeline(payload)
      setPublishedPipelines((current) => [published, ...current])
      setSelectedPublishedPipelineKey(published.key)
      setPublishModalOpen(false)
      message.success(`已发布 pipeline：${published.name}`)
    } catch (error) {
      if (error?.errorFields) return
      message.error(`发布 pipeline 失败: ${error.message}`)
    } finally {
      setPublishSubmitting(false)
    }
  }

  const selectedPublishedPipeline =
    publishedPipelines.find((item) => item.key === selectedPublishedPipelineKey) || publishedPipelines[0] || null

  const headerActions = (
    <Space wrap size={[6, 6]}>
      <Tag color={validationResult?.valid ? 'green' : 'red'}>
        {validationResult?.valid ? '编排校验通过' : '编排待修正'}
      </Tag>
      <Tag color="cyan">固定自定义编排</Tag>
      <Tag color="purple">右侧为共享发布区</Tag>
      <a onClick={loadOverview} style={{ color: '#1677ff' }}>
        <ReloadOutlined /> 刷新
      </a>
    </Space>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card extra={headerActions}>
        <Space direction="vertical" size={6} style={{ width: '100%' }}>
          <Space wrap>
            <ApartmentOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
            <Title level={3} style={{ margin: 0 }}>
              知识计算工作台
            </Title>
            <Tag color="processing">Operator Catalog</Tag>
          </Space>
          <Paragraph style={{ marginBottom: 0, color: '#52607a', maxWidth: 980 }}>
            左侧保留知识计算算子目录；中间固定为用户自定义编排 pipeline；右侧统一展示已发布 pipeline。
            现阶段系统会先把已实现好的系统链路放入发布区，后续用户编排完成并通过校验后，也可以直接发布到数据库，供多人共享和复用。
          </Paragraph>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8} xl={6}>
          <Card>
            <Row gutter={12}>
              <Col span={12}>
                <Statistic title="算子总数" value={operators.length} prefix={<NodeIndexOutlined />} />
              </Col>
              <Col span={12}>
                <Statistic title="已发布链路" value={publishedPipelines.length} prefix={<ShareAltOutlined />} />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} md={16} xl={18}>
          <Card>
            <Space wrap size={[8, 8]}>
              <Tag color="green">已实现 {implementedCount}</Tag>
              <Tag color="gold">规划中 {plannedCount}</Tag>
              <Tag color="geekblue">知识计算目录 {layers.length} 类</Tag>
              <Tag color="volcano">业务扩展 {businessOperatorCount}</Tag>
              <Tag color="cyan">左侧：算子目录</Tag>
              <Tag color="purple">中间：自定义编排</Tag>
              <Tag color="blue">右侧：发布共享</Tag>
            </Space>
          </Card>
        </Col>
      </Row>

      {loading ? (
        <Card>
          <Spin />
        </Card>
      ) : null}

      {!loading && !overview ? (
        <Card>
          <Empty description="暂无知识计算工作台数据" />
        </Card>
      ) : null}

      {!loading && overview ? (
        <>
          <Alert
            type="info"
            showIcon
            message="工作流说明"
            description="左侧拖拽算子到中间构建自定义 pipeline；中间链路会自动做 DTO 契约校验；右侧展示已发布 pipeline，支持一键载入到中间继续编辑。"
          />

          <Row gutter={[16, 16]} align="stretch">
            <Col xs={24} xl={5}>
              <OperatorCatalogPanel
                loading={loading}
                layers={layers}
                operators={filteredOperators}
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                selectedOperatorName={selectedOperatorName}
                onSelectOperator={setSelectedOperatorName}
                onAddOperator={appendOperatorToCustom}
              />
            </Col>

            <Col xs={24} xl={11}>
              <OperatorPipelineCanvas
                mode="custom"
                pipelines={[]}
                currentNodes={customNodes}
                customNodes={customNodes}
                operatorMap={operatorMap}
                selectedPipelineKey=""
                selectedOperatorName={selectedOperatorName}
                onSelectOperator={setSelectedOperatorName}
                onAppendOperator={appendOperatorToCustom}
                onInsertOperator={insertOperatorToCustom}
                onReorderOperator={reorderCustomOperator}
                onRemoveOperator={removeCustomOperator}
                onClearCustomPipeline={clearCustomPipeline}
                validationResult={validationResult}
                validating={validating}
                onExecutePreview={executePreview}
                previewRunning={previewRunning}
                previewResult={previewResult}
                previewDisabledReason={previewDisabledReason}
                headerActions={
                  <Space wrap size={[6, 6]}>
                    <Tag color="processing" icon={<ToolOutlined />}>
                      自定义编排
                    </Tag>
                    <Tag color={validationResult?.valid ? 'green' : 'red'}>
                      {validationResult?.valid ? '校验通过' : '待修正'}
                    </Tag>
                    <a onClick={executePreview} style={{ color: previewDisabledReason ? '#999' : '#1677ff', pointerEvents: previewDisabledReason ? 'none' : 'auto' }}>
                      执行预览
                    </a>
                    <a onClick={openPublishModal} style={{ color: canPublish ? '#1677ff' : '#999', pointerEvents: canPublish ? 'auto' : 'none' }}>
                      发布 pipeline
                    </a>
                    <a onClick={clearCustomPipeline} style={{ color: '#d4380d' }}>
                      清空
                    </a>
                  </Space>
                }
              />
            </Col>

            <Col xs={24} xl={8}>
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <PublishedPipelinePanel
                  pipelines={publishedPipelines}
                  selectedPipelineKey={selectedPublishedPipeline?.key || ''}
                  onSelectPipeline={setSelectedPublishedPipelineKey}
                  onLoadPipeline={loadPublishedPipeline}
                />
                <Card title="当前选中发布链路" styles={{ body: { padding: 16 } }}>
                  {selectedPublishedPipeline ? (
                    <Space direction="vertical" size={10} style={{ width: '100%' }}>
                      <Space wrap>
                        <Text strong style={{ fontSize: 16 }}>
                          {selectedPublishedPipeline.name}
                        </Text>
                        <Tag color={selectedPublishedPipeline.is_builtin ? 'blue' : 'green'}>
                          {selectedPublishedPipeline.is_builtin ? '系统内置' : '用户发布'}
                        </Tag>
                      </Space>
                      <Paragraph style={{ marginBottom: 0, color: '#52607a' }}>
                        {selectedPublishedPipeline.description || '未填写说明。'}
                      </Paragraph>
                      <Space wrap size={[6, 6]}>
                        {(selectedPublishedPipeline.source_types || []).map((item) => (
                          <Tag key={item}>{item}</Tag>
                        ))}
                        <Tag color="geekblue">{(selectedPublishedPipeline.operators || []).length} 个算子</Tag>
                      </Space>
                      <div
                        style={{
                          borderRadius: 12,
                          background: '#f8fbff',
                          border: '1px solid #d7e0ea',
                          padding: 12,
                          maxHeight: 240,
                          overflow: 'auto',
                        }}
                      >
                        <Space direction="vertical" size={8} style={{ width: '100%' }}>
                          {(selectedPublishedPipeline.nodes || []).map((node, index) => (
                            <div key={node.key} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                              <Text>{index + 1}. {node.title || node.operator}</Text>
                              <Tag color="blue">{node.operator}</Tag>
                            </div>
                          ))}
                        </Space>
                      </div>
                    </Space>
                  ) : (
                    <Empty description="请选择一条已发布 pipeline" />
                  )}
                </Card>
              </Space>
            </Col>
          </Row>
        </>
      ) : null}

      <Modal
        title="发布 Pipeline"
        open={publishModalOpen}
        onCancel={() => setPublishModalOpen(false)}
        onOk={handlePublish}
        okText="发布"
        okButtonProps={{ icon: <CloudUploadOutlined />, loading: publishSubmitting, disabled: !canPublish }}
      >
        <Form form={publishForm} layout="vertical">
          <Form.Item
            name="name"
            label="Pipeline 名称"
            rules={[
              { required: true, message: '请输入 pipeline 名称' },
              { min: 2, message: '名称至少 2 个字符' },
            ]}
          >
            <Input placeholder="例如：研报抽取融合链" />
          </Form.Item>
          <Form.Item name="description" label="说明">
            <TextArea rows={4} placeholder="简要描述这条 pipeline 解决什么问题。" />
          </Form.Item>
          <Form.Item name="source_types" label="适用来源（逗号分隔）">
            <Input placeholder="news, report, pdf" />
          </Form.Item>
        </Form>
        {!canPublish ? (
          <Alert
            style={{ marginTop: 12 }}
            type="warning"
            showIcon
            message="当前链路暂不满足发布条件"
            description="只有通过校验、且全部由已实现算子组成，并且以 graph_import 结束的 pipeline 才允许发布。"
          />
        ) : null}
      </Modal>
    </div>
  )
}

export default OperatorWorkbenchPage
