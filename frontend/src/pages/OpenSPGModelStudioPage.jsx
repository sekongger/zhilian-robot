import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Divider,
  Empty,
  Input,
  InputNumber,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Timeline,
  Typography,
  Upload,
  message
} from 'antd'
import {
  ApiOutlined,
  CheckCircleOutlined,
  InboxOutlined,
  PartitionOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  RobotOutlined
} from '@ant-design/icons'
import openspgDemoService from '../services/openspgDemoApi'
import D3ForceGraph from '../components/D3ForceGraph'

const { Title, Text } = Typography
const { TextArea } = Input
const { Dragger } = Upload

const JsonPanel = ({ title, data, height = 220 }) => (
  <Card title={title} size="small" style={{ height: '100%' }}>
    <pre
      style={{
        margin: 0,
        maxHeight: height,
        overflow: 'auto',
        background: '#020617',
        color: '#cbd5e1',
        padding: 12,
        borderRadius: 8,
        border: '1px solid #334155',
        fontSize: 12,
        lineHeight: 1.45,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}
    >
      {JSON.stringify(data ?? {}, null, 2)}
    </pre>
  </Card>
)

const STATUS_COLOR = {
  FINISH: 'green',
  SUCCESS: 'green',
  RUNNING: 'blue',
  WAITING: 'gold',
  FAIL: 'red',
  FAILED: 'red',
  STOP: 'orange'
}

const statusColor = (status) => STATUS_COLOR[String(status || '').toUpperCase()] || 'default'

const defaultInputText = [
  '2月26日，智链机器人有限公司宣布与华东智造集团股份有限公司达成战略合作。',
  '同日，杭州灵巧科技有限公司在产业峰会上发布新一代协作机器人产品。'
].join('\n')

const OpenSPGModelStudioPage = () => {
  const [projectId, setProjectId] = useState(1)
  const [schemaScript, setSchemaScript] = useState('')
  const [schemaLoading, setSchemaLoading] = useState(false)
  const [schemaApplying, setSchemaApplying] = useState(false)
  const [schemaResult, setSchemaResult] = useState(null)
  const [schemaCurrent, setSchemaCurrent] = useState(null)
  const [activeModelProfile, setActiveModelProfile] = useState(null)
  const [activatingModel, setActivatingModel] = useState(false)

  const [textContent, setTextContent] = useState(defaultInputText)
  const [uploadFile, setUploadFile] = useState(null)
  const [jobName, setJobName] = useState('')
  const [splitLength, setSplitLength] = useState(500)
  const [semanticSplit, setSemanticSplit] = useState(false)
  const [schemaConstrainedExtract, setSchemaConstrainedExtract] = useState(true)
  const [submittingExtraction, setSubmittingExtraction] = useState(false)
  const [statusLoading, setStatusLoading] = useState(false)
  const [sampleLoading, setSampleLoading] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [statusResult, setStatusResult] = useState(null)
  const [sampleResult, setSampleResult] = useState(null)
  const [currentJobId, setCurrentJobId] = useState(null)

  const loadSchemaTemplate = async () => {
    setSchemaLoading(true)
    try {
      const data = await openspgDemoService.getModelStudioSchemaTemplate()
      const template = data?.schema_script || ''
      setSchemaScript((prev) => (prev && prev.trim() ? prev : template))
    } catch (error) {
      message.error(`加载 Schema 模板失败: ${error.message}`)
    } finally {
      setSchemaLoading(false)
    }
  }

  const loadSchemaCurrent = async (nextProjectId = projectId) => {
    setSchemaLoading(true)
    try {
      const data = await openspgDemoService.getModelStudioSchemaCurrent(nextProjectId)
      setSchemaCurrent(data)
      if (!schemaScript.trim() && data?.schema_script) {
        setSchemaScript(data.schema_script)
      }
    } catch (error) {
      message.error(`读取当前 Schema 失败: ${error.message}`)
    } finally {
      setSchemaLoading(false)
    }
  }

  const loadActiveModelProfile = async (nextProjectId = projectId) => {
    try {
      const data = await openspgDemoService.getModelStudioActiveSchema(nextProjectId)
      setActiveModelProfile(data || null)
    } catch (error) {
      setActiveModelProfile(null)
    }
  }

  const applySchema = async () => {
    if (!schemaScript.trim()) {
      message.warning('请先填写 Schema DSL')
      return
    }
    setSchemaApplying(true)
    try {
      const data = await openspgDemoService.applyModelStudioSchema({
        project_id: projectId,
        schema_script: schemaScript
      })
      const applySuccess = data?.schema_apply_result?.response?.success
      if (applySuccess === false) {
        const errMsg = data?.schema_apply_result?.response?.errorMsg || data?.schema_apply_result?.response?.message || 'OpenSPG 返回 success=false'
        message.error(`Schema 提交失败: ${errMsg}`)
        return
      }
      setSchemaResult(data)
      setSchemaCurrent(data)
      setActiveModelProfile(data?.active_model_profile || null)
      message.success('Schema 提交完成')
    } catch (error) {
      message.error(`Schema 提交失败: ${error.message}`)
    } finally {
      setSchemaApplying(false)
    }
  }

  const activateCurrentSchema = async () => {
    const script = schemaScript.trim()
    if (!script) {
      message.warning('请先填写 Schema DSL')
      return
    }
    setActivatingModel(true)
    try {
      const data = await openspgDemoService.activateModelStudioSchema({
        project_id: projectId,
        schema_script: script,
        label: 'manual-activate'
      })
      setActiveModelProfile(data || null)
      message.success('已激活到资讯流程')
    } catch (error) {
      message.error(`激活失败: ${error.message}`)
    } finally {
      setActivatingModel(false)
    }
  }

  const submitExtraction = async () => {
    setSubmittingExtraction(true)
    try {
      let data
      if (uploadFile) {
        const formData = new FormData()
        formData.append('file', uploadFile)
        formData.append('project_id', String(projectId))
        formData.append('worker_num', '1')
        if (jobName) {
          formData.append('job_name', jobName)
        }
        formData.append('split_length', String(splitLength))
        formData.append('semantic_split', String(semanticSplit))
        formData.append('schema_constrained_extract', String(schemaConstrainedExtract))
        data = await openspgDemoService.submitModelStudioExtractionFile(formData)
      } else {
        if (!textContent.trim()) {
          message.warning('请先上传文件，或输入要抽取的新闻文本')
          return
        }
        data = await openspgDemoService.submitModelStudioExtraction({
          project_id: projectId,
          text_content: textContent,
          job_name: jobName || undefined,
          worker_num: 1,
          split_length: splitLength,
          semantic_split: semanticSplit,
          schema_constrained_extract: schemaConstrainedExtract
        })
      }
      setSubmitResult(data)
      const jobId = data?.job?.id
      if (jobId) {
        setCurrentJobId(Number(jobId))
        message.success(`抽取任务已提交，jobId=${jobId}`)
      } else {
        message.warning('任务已提交，但未返回 jobId，请检查 OpenSPG 返回')
      }
    } catch (error) {
      message.error(`抽取任务提交失败: ${error.message}`)
    } finally {
      setSubmittingExtraction(false)
    }
  }

  const loadExtractionStatus = async (jobId = currentJobId) => {
    if (!jobId) {
      return
    }
    setStatusLoading(true)
    try {
      const data = await openspgDemoService.getModelStudioExtractionStatus(projectId, jobId)
      setStatusResult(data)
    } catch (error) {
      message.error(`读取抽取过程失败: ${error.message}`)
    } finally {
      setStatusLoading(false)
    }
  }

  const loadExtractionSample = async (jobId = currentJobId) => {
    if (!jobId) {
      return
    }
    setSampleLoading(true)
    try {
      const data = await openspgDemoService.getModelStudioExtractionSample(projectId, jobId)
      setSampleResult(data)
    } catch (error) {
      message.error(`读取抽样结果失败: ${error.message}`)
    } finally {
      setSampleLoading(false)
    }
  }

  const refreshExtraction = async () => {
    if (!currentJobId) {
      message.warning('请先提交抽取任务')
      return
    }
    await Promise.all([loadExtractionStatus(currentJobId), loadExtractionSample(currentJobId)])
  }

  useEffect(() => {
    loadSchemaTemplate()
    loadSchemaCurrent(projectId)
    loadActiveModelProfile(projectId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadActiveModelProfile(projectId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const graphData = useMemo(() => {
    const nodes = (sampleResult?.result_nodes || [])
      .filter((node) => node && typeof node === 'object')
      .map((node) => {
        const properties = (node.properties && typeof node.properties === 'object') ? node.properties : {}
        return {
          id: String(node.id || ''),
          name: String(properties.name || properties.title || node.id || ''),
          type: String(node.label || 'unknown')
        }
      })
      .filter((node) => node.id)

    const nodeIds = new Set(nodes.map((node) => node.id))
    const edges = (sampleResult?.result_edges || [])
      .filter((edge) => edge && typeof edge === 'object')
      .map((edge, idx) => {
        const source = String(edge.from || edge.srcId || '')
        const target = String(edge.to || edge.dstId || '')
        return {
          id: String(edge.id || `edge-${idx + 1}`),
          source,
          target,
          relation: String(edge.label || (edge.properties && edge.properties.name) || 'related')
        }
      })
      .filter((edge) => edge.source && edge.target && nodeIds.has(edge.source) && nodeIds.has(edge.target))

    return { nodes, edges }
  }, [sampleResult])

  const schemaModel = schemaResult?.schema_model || schemaCurrent?.schema_model || {}
  const processTasks = statusResult?.tasks || []
  const entities = sampleResult?.entities || []
  const latestTraceLog = statusResult?.latest_trace_log || ''
  const llmTrace = statusResult?.llm_trace || sampleResult?.llm_trace || submitResult?.llm_trace || {}

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <RobotOutlined style={{ fontSize: 18, color: '#60a5fa' }} />
          <Title level={4} style={{ margin: 0 }}>OpenSPG/KAG 模型管理与抽取工作台</Title>
          <Tag color="blue">独立页面</Tag>
        </Space>
        <Space wrap>
          <Text type="secondary">Project ID</Text>
          <InputNumber min={1} value={projectId} onChange={(v) => setProjectId(Number(v || 1))} />
          <Button icon={<ReloadOutlined />} onClick={() => loadSchemaCurrent(projectId)} loading={schemaLoading}>
            读取当前模型
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => loadActiveModelProfile(projectId)}>
            刷新激活模型
          </Button>
          {activeModelProfile?.schema_hash && (
            <Tag color="processing">已激活: {activeModelProfile.schema_hash}</Tag>
          )}
        </Space>
      </Space>

      <Alert
        type="info"
        showIcon
        message="使用说明"
        description="先在模型管理区提交 Schema DSL，再在抽取区上传 md/txt/docx/pdf（或直接粘贴文本）并提交任务，最后刷新“抽取过程/抽样结果”查看真实 OpenSPG/KAG 执行日志、提示词和实体结果。"
      />

      <Card
        title="1) 模型管理（Schema DSL）"
        extra={
          <Space>
            <Button icon={<ApiOutlined />} onClick={loadSchemaTemplate} loading={schemaLoading}>
              加载模板
            </Button>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={applySchema} loading={schemaApplying}>
              提交 Schema
            </Button>
            <Button onClick={activateCurrentSchema} loading={activatingModel}>
              激活到资讯流程
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <TextArea
            value={schemaScript}
            onChange={(e) => setSchemaScript(e.target.value)}
            autoSize={{ minRows: 10, maxRows: 20 }}
            placeholder="请输入 schema DSL"
          />
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic title="实体类型数" value={schemaModel.entity_count || 0} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic title="关系类型数" value={schemaModel.relation_count || 0} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <Statistic title="实体名称数" value={(schemaModel.entity_names || []).length} />
              </Card>
            </Col>
          </Row>
          {(schemaModel.entity_names || []).length > 0 && (
            <Space wrap>
              {(schemaModel.entity_names || []).map((name) => (
                <Tag key={name} color="geekblue">{name}</Tag>
              ))}
            </Space>
          )}
        </Space>
      </Card>

      <Card
        title="2) 抽取执行（文件上传 / 文本）"
        extra={
          <Space>
            <Button icon={<PlayCircleOutlined />} type="primary" onClick={submitExtraction} loading={submittingExtraction}>
              提交抽取任务
            </Button>
            <Button icon={<ReloadOutlined />} onClick={refreshExtraction} disabled={!currentJobId} loading={statusLoading || sampleLoading}>
              刷新过程与结果
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Space wrap>
            <Text type="secondary">任务名</Text>
            <Input
              value={jobName}
              onChange={(e) => setJobName(e.target.value)}
              placeholder="可选，自定义任务名"
              style={{ width: 320 }}
            />
            <Tag color="cyan">当前 Job ID: {currentJobId || '-'}</Tag>
          </Space>
          <Space wrap>
            <Text type="secondary">分段长度</Text>
            <InputNumber min={100} max={4000} value={splitLength} onChange={(v) => setSplitLength(Number(v || 500))} />
            <Checkbox checked={semanticSplit} onChange={(e) => setSemanticSplit(e.target.checked)}>语义分段</Checkbox>
            <Checkbox checked={schemaConstrainedExtract} onChange={(e) => setSchemaConstrainedExtract(e.target.checked)}>
              按当前 Schema 约束抽取
            </Checkbox>
          </Space>
          <Dragger
            multiple={false}
            maxCount={1}
            accept=".md,.txt,.docx,.pdf"
            beforeUpload={(file) => {
              setUploadFile(file)
              return false
            }}
            onRemove={() => {
              setUploadFile(null)
            }}
            fileList={uploadFile ? [uploadFile] : []}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽上传文件（md/txt/docx/pdf）</p>
            <p className="ant-upload-hint">上传后将调用 OpenSPG 原生上传接口和 KAG Builder 链路执行抽取。</p>
          </Dragger>
          <TextArea
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            autoSize={{ minRows: 6, maxRows: 16 }}
            placeholder="可选：若不上传文件，可直接输入文本（会临时转为 md 后走同一链路）"
          />
        </Space>
      </Card>

      <Card title="3) 抽取过程与结果可视化">
        {!currentJobId ? (
          <Empty description="请先提交抽取任务" />
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small">
                  <Statistic title="任务阶段数" value={processTasks.length} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small">
                  <Statistic title="抽样节点数" value={sampleResult?.counts?.nodes || 0} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small">
                  <Statistic title="实体抽样数" value={sampleResult?.counts?.entities || 0} />
                </Card>
              </Col>
            </Row>

            <Card
              size="small"
              title="模型/提示词/Token"
              extra={<Tag color="purple">{llmTrace?.invoke_mode || 'unknown'}</Tag>}
            >
              {(llmTrace && Object.keys(llmTrace).length > 0) ? (
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Space wrap>
                    <Tag color="blue">Model: {llmTrace.model || '-'}</Tag>
                    <Tag color="cyan">API: {llmTrace.api_base || '-'}</Tag>
                    <Tag color="gold">Prompt Tokens: {llmTrace.prompt_tokens ?? '-'}</Tag>
                    <Tag color="orange">Completion Tokens: {llmTrace.completion_tokens ?? '-'}</Tag>
                    <Tag color="magenta">Total Tokens: {llmTrace.total_tokens ?? '-'}</Tag>
                    <Tag color="geekblue">Prompt Name: {llmTrace.prompt_name || '-'}</Tag>
                  </Space>
                  <Text type="secondary">Prompt</Text>
                  <pre
                    style={{
                      margin: 0,
                      maxHeight: 180,
                      overflow: 'auto',
                      background: '#020617',
                      color: '#cbd5e1',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      padding: 10,
                      fontSize: 12
                    }}
                  >
                    {llmTrace.prompt || '-'}
                  </pre>
                  {(llmTrace.prompts || []).length > 1 && (
                    <Text type="secondary">共记录 {llmTrace.prompts.length} 条提示词（展示最新一条）</Text>
                  )}
                </Space>
              ) : (
                <Empty description="暂无模型执行信息" />
              )}
            </Card>

            <Row gutter={[16, 16]}>
              <Col xs={24} xl={9}>
                <Card
                  size="small"
                  title="执行阶段时间线"
                  extra={<Tag color={statusColor(statusResult?.job?.status)}>{statusResult?.job?.status || '-'}</Tag>}
                >
                  {statusLoading ? (
                    <Spin />
                  ) : processTasks.length === 0 ? (
                    <Empty description="暂无任务阶段明细" />
                  ) : (
                    <Timeline
                      items={processTasks.map((task) => ({
                        color: statusColor(task.status),
                        children: (
                          <Space direction="vertical" size={0}>
                            <Text>{task.type || task.title || `Task-${task.id}`}</Text>
                            <Text type="secondary">状态: {task.status || '-'}</Text>
                          </Space>
                        )
                      }))}
                    />
                  )}
                  <Divider style={{ margin: '12px 0' }} />
                  <Text type="secondary">最新日志</Text>
                  <pre
                    style={{
                      marginTop: 8,
                      maxHeight: 180,
                      overflow: 'auto',
                      background: '#020617',
                      color: '#cbd5e1',
                      border: '1px solid #334155',
                      borderRadius: 8,
                      padding: 10,
                      fontSize: 12
                    }}
                  >
                    {latestTraceLog || '暂无日志'}
                  </pre>
                </Card>
              </Col>
              <Col xs={24} xl={15}>
                <Card
                  size="small"
                  title="抽样子图"
                  extra={<PartitionOutlined />}
                >
                  {sampleLoading ? (
                    <Spin />
                  ) : graphData.nodes.length === 0 ? (
                    <Empty description="暂无抽样图数据" />
                  ) : (
                    <D3ForceGraph data={graphData} />
                  )}
                </Card>
              </Col>
            </Row>

            <Card size="small" title="实体抽样列表">
              <Table
                rowKey="id"
                size="small"
                pagination={{ pageSize: 8 }}
                dataSource={entities}
                columns={[
                  { title: '实体ID', dataIndex: 'id', width: 240 },
                  { title: '实体名称', dataIndex: 'name' },
                  {
                    title: '类型',
                    dataIndex: 'label',
                    width: 120,
                    render: (value) => <Tag color="blue">{value || 'Unknown'}</Tag>
                  },
                  {
                    title: '证据片段',
                    dataIndex: 'snippet',
                    render: (value) => <Text type="secondary">{value || '-'}</Text>,
                    ellipsis: true
                  }
                ]}
              />
            </Card>

            <Row gutter={[16, 16]}>
              <Col xs={24} xl={12}>
                <JsonPanel title="任务提交返回(JSON)" data={submitResult} />
              </Col>
              <Col xs={24} xl={12}>
                <JsonPanel title="任务状态返回(JSON)" data={statusResult} />
              </Col>
              <Col xs={24} xl={24}>
                <JsonPanel title="抽样结果返回(JSON)" data={sampleResult} height={260} />
              </Col>
            </Row>
          </Space>
        )}
      </Card>
    </Space>
  )
}

export default OpenSPGModelStudioPage
