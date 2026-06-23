import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
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
  message
} from 'antd'
import {
  ApiOutlined,
  ArrowRightOutlined,
  BuildOutlined,
  CheckCircleOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  RocketOutlined
} from '@ant-design/icons'
import openspgDemoService from '../services/openspgDemoApi'

const { Title, Text } = Typography
const { TextArea } = Input

const STEP_DEFS = [
  { key: 'collect', title: '1. 采集', desc: '拉取实时资讯' },
  { key: 'process', title: '2. 处理', desc: '批次预览与状态' },
  { key: 'model', title: '3. 加工', desc: 'Schema 管理与激活' },
  { key: 'execute', title: '4. 执行', desc: 'Bridge + Builder' },
  { key: 'apply', title: '5. 应用', desc: '头条结果与洞察' }
]

const STEP_STATUS_COLOR = {
  idle: 'default',
  running: 'processing',
  done: 'success',
  error: 'error'
}

const JsonPanel = ({ title, data, height = 240 }) => (
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

const initialStepStatus = STEP_DEFS.reduce((acc, step) => {
  acc[step.key] = { status: 'idle', error: '', updatedAt: '' }
  return acc
}, {})

const formatTime = (value) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', { hour12: false })
}

const KAGWorkflowPage = () => {
  const [projectId, setProjectId] = useState(1)
  const [ingestHours, setIngestHours] = useState(24)
  const [ingestMaxEntries, setIngestMaxEntries] = useState(5)
  const [bridgeLimit, setBridgeLimit] = useState(50)
  const [topN, setTopN] = useState(20)
  const [builderCommand, setBuilderCommand] = useState('')
  const [submitBuilder, setSubmitBuilder] = useState(true)
  const [historyLimit, setHistoryLimit] = useState(20)
  const [activeStep, setActiveStep] = useState(0)
  const [stepStatus, setStepStatus] = useState(initialStepStatus)

  const [pageLoading, setPageLoading] = useState(true)
  const [runningCollect, setRunningCollect] = useState(false)
  const [runningProcess, setRunningProcess] = useState(false)
  const [runningModel, setRunningModel] = useState(false)
  const [runningExecute, setRunningExecute] = useState(false)
  const [runningApply, setRunningApply] = useState(false)
  const [runningWorkflow, setRunningWorkflow] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [replayingRunId, setReplayingRunId] = useState('')

  const [ingestResult, setIngestResult] = useState(null)
  const [bridgePreview, setBridgePreview] = useState(null)
  const [bridgeStatus, setBridgeStatus] = useState(null)
  const [schemaScript, setSchemaScript] = useState('')
  const [schemaCurrent, setSchemaCurrent] = useState(null)
  const [schemaApplyResult, setSchemaApplyResult] = useState(null)
  const [activeModelProfile, setActiveModelProfile] = useState(null)
  const [bridgeRun, setBridgeRun] = useState(null)
  const [headlinesData, setHeadlinesData] = useState({ headlines: [], stats: {}, meta: {} })
  const [workflowRun, setWorkflowRun] = useState(null)
  const [workflowHistory, setWorkflowHistory] = useState([])
  const [headlinesSnapshot, setHeadlinesSnapshot] = useState(null)

  const setStep = (key, status, extra = {}) => {
    setStepStatus((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] || { status: 'idle', error: '', updatedAt: '' }),
        status,
        updatedAt: new Date().toISOString(),
        ...extra
      }
    }))
  }

  const withStep = async (key, fn) => {
    setStep(key, 'running', { error: '' })
    try {
      const result = await fn()
      setStep(key, 'done', { error: '' })
      return result
    } catch (error) {
      setStep(key, 'error', { error: error.message || '未知错误' })
      throw error
    }
  }

  const loadSchemaCurrent = async (nextProjectId = projectId) => {
    const data = await openspgDemoService.getModelStudioSchemaCurrent(nextProjectId)
    setSchemaCurrent(data || null)
    if (!schemaScript.trim() && data?.schema_script) {
      setSchemaScript(data.schema_script)
    }
    return data
  }

  const loadActiveModel = async (nextProjectId = projectId) => {
    try {
      const data = await openspgDemoService.getModelStudioActiveSchema(nextProjectId)
      setActiveModelProfile(data || null)
      return data
    } catch (error) {
      setActiveModelProfile(null)
      return null
    }
  }

  const loadHistory = async (nextProjectId = projectId, nextLimit = historyLimit) => {
    setLoadingHistory(true)
    try {
      const data = await openspgDemoService.getNewsWorkflowHistory(nextProjectId, nextLimit)
      setWorkflowHistory(Array.isArray(data?.runs) ? data.runs : [])
    } catch (error) {
      setWorkflowHistory([])
      message.warning(`读取历史回放失败: ${error.message}`)
    } finally {
      setLoadingHistory(false)
    }
  }

  const loadLatestWorkflow = async (nextProjectId = projectId) => {
    try {
      const data = await openspgDemoService.getLatestNewsWorkflowRun(nextProjectId)
      setWorkflowRun(data || null)
      setHeadlinesSnapshot(data?.headlines_snapshot || null)
    } catch (error) {
      setWorkflowRun(null)
      setHeadlinesSnapshot(null)
    }
  }

  const hydrateByWorkflowRun = (run) => {
    if (!run || typeof run !== 'object') {
      return
    }
    setWorkflowRun(run)
    setIngestResult(run.ingest_result || null)
    setBridgeRun(run.bridge_run || null)
    setBridgeStatus(run.bridge_status || null)
    setSchemaApplyResult(run.schema_apply_result || null)
    setActiveModelProfile(run.active_model_profile || null)
    setHeadlinesSnapshot(run.headlines_snapshot || null)
    if (run?.active_model_profile?.schema_script) {
      setSchemaScript(run.active_model_profile.schema_script)
    }
    setStepStatus((prev) => ({
      ...prev,
      collect: { ...prev.collect, status: run.ingest_result ? 'done' : prev.collect.status },
      process: { ...prev.process, status: run.bridge_status || run.bridge_run ? 'done' : prev.process.status },
      model: { ...prev.model, status: run.schema_apply_result ? 'done' : prev.model.status },
      execute: { ...prev.execute, status: run.bridge_run ? 'done' : prev.execute.status },
      apply: { ...prev.apply, status: run.headlines_snapshot ? 'done' : prev.apply.status }
    }))
  }

  const initializePage = async (nextProjectId = projectId) => {
    setPageLoading(true)
    try {
      await Promise.all([
        loadSchemaCurrent(nextProjectId),
        loadActiveModel(nextProjectId),
        loadLatestWorkflow(nextProjectId),
        loadHistory(nextProjectId, historyLimit)
      ])
    } catch (error) {
      message.warning(`初始化数据失败: ${error.message}`)
    } finally {
      setPageLoading(false)
    }
  }

  const runCollect = async () => {
    setRunningCollect(true)
    try {
      await withStep('collect', async () => {
        const data = await openspgDemoService.pullRealRss({
          max_entries_per_feed: ingestMaxEntries,
          hours_ago: ingestHours
        })
        setIngestResult(data || null)
        message.success(`采集完成：新增 ${data?.inserted_count || 0} 条`)
        return data
      })
    } catch (error) {
      message.error(`采集失败: ${error.message}`)
    } finally {
      setRunningCollect(false)
    }
  }

  const runProcess = async () => {
    setRunningProcess(true)
    try {
      await withStep('process', async () => {
        const [previewData, statusData] = await Promise.all([
          openspgDemoService.getBridgeBatchPreview({
            limit: bridgeLimit,
            sample_lines: 5,
            allow_demo_fallback: false
          }),
          openspgDemoService.getBridgeStatus()
        ])
        setBridgePreview(previewData || null)
        setBridgeStatus(statusData || null)
        return { previewData, statusData }
      })
      message.success('处理阶段数据已刷新')
    } catch (error) {
      message.error(`处理阶段失败: ${error.message}`)
    } finally {
      setRunningProcess(false)
    }
  }

  const runModel = async () => {
    if (!schemaScript.trim()) {
      message.warning('请先填写或加载 Schema DSL')
      return
    }
    setRunningModel(true)
    try {
      await withStep('model', async () => {
        const applyData = await openspgDemoService.applyModelStudioSchema({
          project_id: projectId,
          schema_script: schemaScript
        })
        setSchemaApplyResult(applyData || null)
        setSchemaCurrent(applyData || null)
        const activated = await openspgDemoService.activateModelStudioSchema({
          project_id: projectId,
          schema_script: schemaScript,
          label: 'kag-workflow'
        })
        setActiveModelProfile(activated || null)
        return { applyData, activated }
      })
      message.success('加工阶段完成：Schema 已提交并激活')
    } catch (error) {
      message.error(`加工阶段失败: ${error.message}`)
    } finally {
      setRunningModel(false)
    }
  }

  const runExecute = async () => {
    setRunningExecute(true)
    try {
      const runData = await withStep('execute', async () => {
        const runData = await openspgDemoService.runBridgeBatch({
          project_id: projectId,
          limit: bridgeLimit,
          force_full: true,
          submit_builder: submitBuilder,
          worker_num: 1,
          use_active_model: true,
          builder_command: builderCommand || undefined
        })
        setBridgeRun(runData || null)
        await Promise.all([runProcess(), loadActiveModel(projectId)])
        return runData
      })
      message.success(`执行完成：导出 ${runData?.export_count || 0} 条`)
    } catch (error) {
      message.error(`执行阶段失败: ${error.message}`)
    } finally {
      setRunningExecute(false)
    }
  }

  const runApply = async () => {
    setRunningApply(true)
    try {
      await withStep('apply', async () => {
        const data = await openspgDemoService.getHeadlines({
          hours: ingestHours,
          top_n: topN,
          allow_demo_fallback: false
        })
        setHeadlinesData(data || { headlines: [], stats: {}, meta: {} })
        return data
      })
      message.success('应用阶段完成：头条结果已更新')
    } catch (error) {
      message.error(`应用阶段失败: ${error.message}`)
    } finally {
      setRunningApply(false)
    }
  }

  const runFullWorkflow = async () => {
    setRunningWorkflow(true)
    try {
      const data = await openspgDemoService.runNewsWorkflow({
        project_id: projectId,
        max_entries_per_feed: ingestMaxEntries,
        hours_ago: ingestHours,
        bridge_limit: bridgeLimit,
        force_full: true,
        submit_builder: submitBuilder,
        worker_num: 1,
        builder_command: builderCommand || undefined,
        headlines_top_n: topN
      })
      hydrateByWorkflowRun(data || {})
      setStep('collect', 'done')
      setStep('process', 'done')
      setStep('model', 'done')
      setStep('execute', 'done')
      setStep('apply', 'done')
      try {
        const headlineData = await openspgDemoService.getHeadlines({
          hours: ingestHours,
          top_n: topN,
          allow_demo_fallback: false
        })
        setHeadlinesData(headlineData || { headlines: [], stats: {}, meta: {} })
      } catch (error) {
        message.warning(`workflow 已完成，但刷新头条列表失败: ${error.message}`)
      }
      await loadHistory(projectId, historyLimit)
      message.success(`一键流程完成：run_id=${data?.run_id || '-'}`)
    } catch (error) {
      message.error(`一键流程失败: ${error.message}`)
    } finally {
      setRunningWorkflow(false)
    }
  }

  const replayHistoryRun = async (runId) => {
    setReplayingRunId(runId)
    try {
      const data = await openspgDemoService.getNewsWorkflowRun(runId)
      hydrateByWorkflowRun(data || {})
      setActiveStep(4)
      message.success(`已回放 run_id=${runId}`)
    } catch (error) {
      message.error(`回放失败: ${error.message}`)
    } finally {
      setReplayingRunId('')
    }
  }

  useEffect(() => {
    initializePage(projectId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const currentStep = STEP_DEFS[activeStep] || STEP_DEFS[0]
  const schemaModel = schemaApplyResult?.schema_model || schemaCurrent?.schema_model || {}
  const previewRecords = bridgePreview?.sample_records || []
  const headlinesRows = headlinesData?.headlines || []

  const historyColumns = useMemo(
    () => [
      {
        title: 'Run ID',
        dataIndex: 'run_id',
        key: 'run_id',
        width: 240,
        render: (value) => <Text code>{value}</Text>
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 100,
        render: (value) => (
          <Tag color={String(value || '').toLowerCase() === 'success' ? 'green' : 'orange'}>
            {value || '-'}
          </Tag>
        )
      },
      {
        title: '开始时间',
        dataIndex: 'started_at',
        key: 'started_at',
        width: 180,
        render: (value) => <Text type="secondary">{formatTime(value)}</Text>
      },
      {
        title: '结束时间',
        dataIndex: 'finished_at',
        key: 'finished_at',
        width: 180,
        render: (value) => <Text type="secondary">{formatTime(value)}</Text>
      },
      {
        title: '导出量',
        dataIndex: ['bridge_run', 'export_count'],
        key: 'export_count',
        width: 90,
        render: (value) => value || 0
      },
      {
        title: '操作',
        key: 'action',
        width: 120,
        render: (_, record) => (
          <Button
            size="small"
            icon={<HistoryOutlined />}
            loading={replayingRunId === record.run_id}
            onClick={() => replayHistoryRun(record.run_id)}
          >
            回放
          </Button>
        )
      }
    ],
    [replayingRunId]
  )

  const headlineColumns = useMemo(
    () => [
      { title: '头条事件', dataIndex: 'headline_title', key: 'headline_title' },
      {
        title: '类型',
        dataIndex: 'event_type_zh',
        key: 'event_type_zh',
        width: 120,
        render: (value) => value || '-'
      },
      {
        title: '企业数量',
        dataIndex: 'companies',
        key: 'companies',
        width: 90,
        render: (items = []) => items.length
      },
      {
        title: '头条分',
        dataIndex: 'headline_score',
        key: 'headline_score',
        width: 100
      },
      {
        title: '最新时间',
        dataIndex: 'latest_publish_time',
        key: 'latest_publish_time',
        width: 180,
        render: (value) => formatTime(value)
      }
    ],
    []
  )

  const renderCollectPanel = () => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Text type="secondary">窗口小时</Text>
        <InputNumber min={1} max={168} value={ingestHours} onChange={(v) => setIngestHours(Number(v || 24))} />
        <Text type="secondary">每源条数</Text>
        <InputNumber min={1} max={50} value={ingestMaxEntries} onChange={(v) => setIngestMaxEntries(Number(v || 5))} />
        <Button type="primary" icon={<PlayCircleOutlined />} loading={runningCollect} onClick={runCollect}>
          执行采集
        </Button>
      </Space>
      {ingestResult ? (
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="新增">{ingestResult.inserted_count || 0}</Descriptions.Item>
          <Descriptions.Item label="抓取">{ingestResult.fetched_count || 0}</Descriptions.Item>
          <Descriptions.Item label="重复">{ingestResult.duplicate_count || 0}</Descriptions.Item>
          <Descriptions.Item label="状态">{ingestResult.status || '-'}</Descriptions.Item>
        </Descriptions>
      ) : (
        <Empty description="尚未执行采集" />
      )}
      <JsonPanel title="采集产物(JSON)" data={ingestResult} />
    </Space>
  )

  const renderProcessPanel = () => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Text type="secondary">Bridge 限制</Text>
        <InputNumber min={1} max={5000} value={bridgeLimit} onChange={(v) => setBridgeLimit(Number(v || 50))} />
        <Button type="primary" icon={<PlayCircleOutlined />} loading={runningProcess} onClick={runProcess}>
          执行处理
        </Button>
      </Space>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <JsonPanel title="处理产物: Bridge 预览" data={bridgePreview} />
        </Col>
        <Col xs={24} lg={12}>
          <JsonPanel title="处理产物: Bridge 状态" data={bridgeStatus} />
        </Col>
      </Row>
      <Card size="small" title="样例记录">
        <Table
          size="small"
          rowKey={(record) => record.doc_hash || record.doc_id}
          pagination={{ pageSize: 5 }}
          dataSource={previewRecords}
          columns={[
            { title: 'doc_id', dataIndex: 'doc_id', width: 210 },
            { title: '标题', dataIndex: 'title', ellipsis: true },
            { title: '时间', dataIndex: 'publish_time', width: 160 }
          ]}
        />
      </Card>
    </Space>
  )

  const renderModelPanel = () => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Text type="secondary">Project ID</Text>
        <InputNumber min={1} value={projectId} onChange={(v) => setProjectId(Number(v || 1))} />
        <Button icon={<ReloadOutlined />} onClick={() => loadSchemaCurrent(projectId)}>
          读取当前 Schema
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => loadActiveModel(projectId)}>
          刷新激活模型
        </Button>
        <Button type="primary" icon={<BuildOutlined />} loading={runningModel} onClick={runModel}>
          提交并激活
        </Button>
      </Space>
      <TextArea
        value={schemaScript}
        onChange={(e) => setSchemaScript(e.target.value)}
        autoSize={{ minRows: 8, maxRows: 16 }}
        placeholder="请输入 Schema DSL"
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="实体类型" value={schemaModel.entity_count || 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="关系类型" value={schemaModel.relation_count || 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="激活模型" value={activeModelProfile?.schema_hash ? 1 : 0} /></Card>
        </Col>
      </Row>
      <Space wrap>
        {activeModelProfile?.schema_hash ? (
          <Tag color="processing">当前激活: {activeModelProfile.schema_hash}</Tag>
        ) : (
          <Tag>未激活</Tag>
        )}
        {(schemaModel.entity_names || []).slice(0, 10).map((name) => (
          <Tag key={name} color="blue">{name}</Tag>
        ))}
      </Space>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <JsonPanel title="加工产物: Schema 应用结果" data={schemaApplyResult} />
        </Col>
        <Col xs={24} lg={12}>
          <JsonPanel title="加工产物: 激活模型" data={activeModelProfile} />
        </Col>
      </Row>
    </Space>
  )

  const renderExecutePanel = () => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Checkbox checked={submitBuilder} onChange={(e) => setSubmitBuilder(e.target.checked)}>
          提交 Builder
        </Checkbox>
        <Input
          style={{ width: 420, maxWidth: '100%' }}
          value={builderCommand}
          onChange={(e) => setBuilderCommand(e.target.value)}
          placeholder="可选：自定义 builder command"
        />
        <Button type="primary" icon={<RocketOutlined />} loading={runningExecute} onClick={runExecute}>
          执行 Bridge
        </Button>
      </Space>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="导出量" value={bridgeRun?.export_count || 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="耗时(ms)" value={bridgeRun?.elapsed_ms || 0} /></Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small"><Statistic title="Builder模式" value={bridgeRun?.builder_submit_result?.mode || '-'} /></Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <JsonPanel title="执行产物: Bridge Run" data={bridgeRun} />
        </Col>
        <Col xs={24} lg={12}>
          <JsonPanel title="执行产物: Bridge 状态" data={bridgeStatus} />
        </Col>
      </Row>
    </Space>
  )

  const renderApplyPanel = () => (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap>
        <Text type="secondary">Top N</Text>
        <InputNumber min={1} max={100} value={topN} onChange={(v) => setTopN(Number(v || 20))} />
        <Button type="primary" icon={<ApiOutlined />} loading={runningApply} onClick={runApply}>
          刷新头条结果
        </Button>
      </Space>
      <Card size="small" title="应用产物: 头条列表">
        <Table
          size="small"
          rowKey={(record) => record.event_id}
          pagination={{ pageSize: 8 }}
          dataSource={headlinesRows}
          columns={headlineColumns}
        />
      </Card>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <JsonPanel title="应用产物: 头条统计" data={headlinesData?.stats || {}} />
        </Col>
        <Col xs={24} lg={12}>
          <JsonPanel title="历史回放快照" data={headlinesSnapshot} />
        </Col>
      </Row>
    </Space>
  )

  const renderStepPanel = () => {
    if (currentStep.key === 'collect') return renderCollectPanel()
    if (currentStep.key === 'process') return renderProcessPanel()
    if (currentStep.key === 'model') return renderModelPanel()
    if (currentStep.key === 'execute') return renderExecutePanel()
    return renderApplyPanel()
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <RocketOutlined style={{ fontSize: 18, color: '#60a5fa' }} />
          <Title level={4} style={{ margin: 0 }}>KAG 全流程处理</Title>
          <Tag color="blue">分期1/2/3</Tag>
        </Space>
        <Space wrap>
          <Text type="secondary">Project ID</Text>
          <InputNumber min={1} value={projectId} onChange={(v) => setProjectId(Number(v || 1))} />
          <Button icon={<ReloadOutlined />} onClick={() => initializePage(projectId)}>
            刷新页面数据
          </Button>
          <Button
            type="primary"
            icon={<CheckCircleOutlined />}
            loading={runningWorkflow}
            onClick={runFullWorkflow}
          >
            一键跑通全流程
          </Button>
        </Space>
      </Space>

      <Alert
        type="info"
        showIcon
        message="流程说明"
        description="点击上方流程节点，按“采集 → 处理 → 加工 → 执行 → 应用”逐步操作；每一步都可查看产物。你也可以直接使用“一键跑通全流程”，然后在历史回放中按 run_id 回放。"
      />

      <Card size="small" title="流程导航">
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', overflowX: 'auto', paddingBottom: 4 }}>
          {STEP_DEFS.map((step, idx) => (
            <React.Fragment key={step.key}>
              <Card
                size="small"
                hoverable
                onClick={() => setActiveStep(idx)}
                style={{
                  minWidth: 220,
                  cursor: 'pointer',
                  border: activeStep === idx ? '1px solid #3b82f6' : '1px solid #334155',
                  background: activeStep === idx ? 'rgba(59, 130, 246, 0.08)' : '#111827'
                }}
              >
                <Space direction="vertical" size={4}>
                  <Space>
                    <Text strong>{step.title}</Text>
                    <Tag color={STEP_STATUS_COLOR[stepStatus[step.key]?.status || 'idle']}>
                      {stepStatus[step.key]?.status || 'idle'}
                    </Tag>
                  </Space>
                  <Text type="secondary">{step.desc}</Text>
                </Space>
              </Card>
              {idx < STEP_DEFS.length - 1 && <ArrowRightOutlined style={{ color: '#64748b' }} />}
            </React.Fragment>
          ))}
        </div>
      </Card>

      <Card
        title={`${currentStep.title} · ${currentStep.desc}`}
        extra={
          <Space>
            {stepStatus[currentStep.key]?.error ? (
              <Tag color="error">{stepStatus[currentStep.key].error}</Tag>
            ) : (
              <Tag>{formatTime(stepStatus[currentStep.key]?.updatedAt)}</Tag>
            )}
          </Space>
        }
      >
        {pageLoading ? <Spin /> : renderStepPanel()}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={10}>
          <Card
            title="分期2：一键 Workflow 运行详情"
            extra={
              <Button icon={<ReloadOutlined />} onClick={() => loadLatestWorkflow(projectId)}>
                刷新 latest
              </Button>
            }
          >
            {!workflowRun ? (
              <Empty description="暂无 workflow 运行记录" />
            ) : (
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="Run ID">{workflowRun.run_id || '-'}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={workflowRun.status === 'success' ? 'green' : 'orange'}>{workflowRun.status || '-'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="开始">{formatTime(workflowRun.started_at)}</Descriptions.Item>
                  <Descriptions.Item label="结束">{formatTime(workflowRun.finished_at)}</Descriptions.Item>
                </Descriptions>
                <Timeline
                  items={[
                    { color: ingestResult ? 'green' : 'gray', children: '采集' },
                    { color: bridgePreview || bridgeStatus ? 'green' : 'gray', children: '处理' },
                    { color: schemaApplyResult ? 'green' : 'gray', children: '加工' },
                    { color: bridgeRun ? 'green' : 'gray', children: '执行' },
                    { color: headlinesSnapshot || headlinesRows.length > 0 ? 'green' : 'gray', children: '应用' }
                  ]}
                />
                <JsonPanel title="Workflow 产物(JSON)" data={workflowRun} />
              </Space>
            )}
          </Card>
        </Col>
        <Col xs={24} xl={14}>
          <Card
            title="分期3：历史回放"
            extra={
              <Space>
                <InputNumber min={1} max={100} value={historyLimit} onChange={(v) => setHistoryLimit(Number(v || 20))} />
                <Button loading={loadingHistory} icon={<ReloadOutlined />} onClick={() => loadHistory(projectId, historyLimit)}>
                  刷新历史
                </Button>
              </Space>
            }
          >
            <Table
              rowKey="run_id"
              size="small"
              loading={loadingHistory}
              pagination={{ pageSize: 8 }}
              dataSource={workflowHistory}
              columns={historyColumns}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

export default KAGWorkflowPage
