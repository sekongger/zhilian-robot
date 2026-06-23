import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Input,
  InputNumber,
  message,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Timeline,
  Table,
  Tabs,
  Tag,
  Typography,
  Collapse
} from 'antd'
import {
  ApiOutlined,
  BuildOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  PartitionOutlined,
  FireOutlined
} from '@ant-design/icons'
import openspgDemoService from '../services/openspgDemoApi'

const { Title, Text } = Typography

const EVENT_TYPE_COLOR = {
  cooperation: 'blue',
  financing: 'gold',
  product_release: 'green',
  order: 'purple',
  capacity_expansion: 'cyan',
  policy: 'red'
}

const JsonPanel = ({ title, data, extra, height = 280 }) => (
  <Card title={title} extra={extra} size="small" style={{ height: '100%' }}>
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
        lineHeight: 1.45
      }}
    >
      {JSON.stringify(data ?? {}, null, 2)}
    </pre>
  </Card>
)

const OpenSPGKagHeadlinesPage = () => {
  const navigate = useNavigate()
  const [loadingHeadlines, setLoadingHeadlines] = useState(false)
  const [loadingSnapshot, setLoadingSnapshot] = useState(false)
  const [loadingEngineHealth, setLoadingEngineHealth] = useState(false)
  const [loadingBridgePreview, setLoadingBridgePreview] = useState(false)
  const [loadingBridgeStatus, setLoadingBridgeStatus] = useState(false)
  const [runningBridge, setRunningBridge] = useState(false)
  const [loadingIngest, setLoadingIngest] = useState(false)
  const [runningRealLoop, setRunningRealLoop] = useState(false)
  const [runningWorkflow, setRunningWorkflow] = useState(false)
  const [hours, setHours] = useState(24)
  const [topN, setTopN] = useState(20)
  const [projectId, setProjectId] = useState(1)
  const [bridgeLimit, setBridgeLimit] = useState(50)
  const [bridgeSubmitBuilder, setBridgeSubmitBuilder] = useState(true)
  const [bridgeCommand, setBridgeCommand] = useState('')
  const [ingestHours, setIngestHours] = useState(24)
  const [ingestMaxEntries, setIngestMaxEntries] = useState(5)
  const [headlinesData, setHeadlinesData] = useState({ headlines: [], stats: {}, meta: {} })
  const [engineSnapshot, setEngineSnapshot] = useState(null)
  const [engineHealth, setEngineHealth] = useState(null)
  const [bridgePreview, setBridgePreview] = useState(null)
  const [bridgeStatus, setBridgeStatus] = useState(null)
  const [ingestResult, setIngestResult] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [activeModelProfile, setActiveModelProfile] = useState(null)
  const [workflowRun, setWorkflowRun] = useState(null)

  const loadHeadlines = async (nextHours = hours, nextTopN = topN) => {
    setLoadingHeadlines(true)
    try {
      const data = await openspgDemoService.getHeadlines({
        hours: nextHours,
        top_n: nextTopN,
        allow_demo_fallback: false
      })
      setHeadlinesData(data || { headlines: [], stats: {}, meta: {} })
    } catch (error) {
      message.error(`加载产业头条失败: ${error.message}`)
    } finally {
      setLoadingHeadlines(false)
    }
  }

  const loadEngineSnapshot = async (nextProjectId = projectId) => {
    setLoadingSnapshot(true)
    try {
      const data = await openspgDemoService.getEngineSnapshot(nextProjectId)
      setEngineSnapshot(data)
    } catch (error) {
      message.error(`加载 OpenSPG 引擎演示失败: ${error.message}`)
    } finally {
      setLoadingSnapshot(false)
    }
  }

  const loadEngineHealth = async (nextProjectId = projectId) => {
    setLoadingEngineHealth(true)
    try {
      const data = await openspgDemoService.getEngineHealth(nextProjectId)
      setEngineHealth(data)
    } catch (error) {
      message.error(`加载 OpenSPG 健康状态失败: ${error.message}`)
    } finally {
      setLoadingEngineHealth(false)
    }
  }

  const loadBridgePreview = async (nextLimit = bridgeLimit) => {
    setLoadingBridgePreview(true)
    try {
      const data = await openspgDemoService.getBridgeBatchPreview({
        limit: nextLimit,
        sample_lines: 5,
        allow_demo_fallback: false
      })
      setBridgePreview(data)
    } catch (error) {
      message.error(`加载 Builder 输入批次预览失败: ${error.message}`)
    } finally {
      setLoadingBridgePreview(false)
    }
  }

  const loadBridgeStatus = async () => {
    setLoadingBridgeStatus(true)
    try {
      const data = await openspgDemoService.getBridgeStatus()
      setBridgeStatus(data)
    } catch (error) {
      message.error(`加载桥接状态失败: ${error.message}`)
    } finally {
      setLoadingBridgeStatus(false)
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

  const loadLatestWorkflowRun = async (nextProjectId = projectId) => {
    try {
      const data = await openspgDemoService.getLatestNewsWorkflowRun(nextProjectId)
      setWorkflowRun(data || null)
    } catch (error) {
      setWorkflowRun(null)
    }
  }

  const triggerBridgeRun = async ({ forceFull = false, submitBuilder = bridgeSubmitBuilder } = {}) => {
    setRunningBridge(true)
    try {
      const data = await openspgDemoService.runBridgeBatch({
        limit: bridgeLimit,
        force_full: forceFull,
        submit_builder: submitBuilder,
        project_id: projectId,
        builder_command: bridgeCommand || undefined,
        worker_num: 1
      })
      const builderResult = data?.builder_submit_result || {}
      const builderNote = builderResult.mode === 'live'
        ? '，Builder 已提交'
        : builderResult.mode === 'skip'
          ? `，Builder 未提交（${builderResult.reason || 'skip'}）`
          : ''
      message.success(
        `桥接完成：导出 ${data.export_count || 0} 条${builderNote}`
      )
      if (builderResult.mode === 'skip' && builderResult.hint) {
        message.info(builderResult.hint)
      }
      await Promise.all([loadBridgeStatus(), loadBridgePreview(bridgeLimit), loadEngineHealth(projectId)])
    } catch (error) {
      message.error(`执行桥接失败: ${error.message}`)
    } finally {
      setRunningBridge(false)
    }
  }

  const pullRealRss = async () => {
    setLoadingIngest(true)
    try {
      const data = await openspgDemoService.pullRealRss({
        max_entries_per_feed: ingestMaxEntries,
        hours_ago: ingestHours
      })
      setIngestResult(data)
      message.success(`实时资讯拉取完成：新增 ${data.inserted_count || 0} 条`)
      await Promise.all([loadHeadlines(hours, topN), loadBridgePreview(bridgeLimit), loadBridgeStatus()])
    } catch (error) {
      message.error(`拉取实时资讯失败: ${error.message}`)
    } finally {
      setLoadingIngest(false)
    }
  }

  const runFullRealLoop = async () => {
    setRunningRealLoop(true)
    try {
      const ingest = await openspgDemoService.pullRealRss({
        max_entries_per_feed: ingestMaxEntries,
        hours_ago: ingestHours
      })
      setIngestResult(ingest)
      // 演示入口固定全量桥接，避免增量游标导致“拉取有新增但导出为 0”的体验问题。
      const useForceFull = true
      const bridge = await openspgDemoService.runBridgeBatch({
        limit: bridgeLimit,
        force_full: useForceFull,
        submit_builder: bridgeSubmitBuilder,
        project_id: projectId,
        builder_command: bridgeCommand || undefined,
        worker_num: 1
      })
      const builderResult = bridge?.builder_submit_result || {}
      const builderNote = builderResult.mode === 'live'
        ? '，Builder 已提交'
        : builderResult.mode === 'skip'
          ? `，Builder 未提交（${builderResult.reason || 'skip'}）`
          : ''
      message.success(
        `全真实闭环已执行：拉取 ${ingest.inserted_count || 0} 条，桥接导出 ${bridge.export_count || 0} 条（全量）${builderNote}`
      )
      if (builderResult.mode === 'skip' && builderResult.hint) {
        message.info(builderResult.hint)
      }
      await Promise.all([
        loadHeadlines(hours, topN),
        loadBridgePreview(bridgeLimit),
        loadBridgeStatus(),
        loadEngineHealth(projectId),
        loadEngineSnapshot(projectId)
      ])
    } catch (error) {
      message.error(`执行全真实闭环失败: ${error.message}`)
    } finally {
      setRunningRealLoop(false)
    }
  }

  const runNewsWorkflowByActiveModel = async () => {
    setRunningWorkflow(true)
    try {
      const data = await openspgDemoService.runNewsWorkflow({
        project_id: projectId,
        max_entries_per_feed: ingestMaxEntries,
        hours_ago: ingestHours,
        bridge_limit: bridgeLimit,
        force_full: true,
        submit_builder: bridgeSubmitBuilder,
        worker_num: 1,
        builder_command: bridgeCommand || undefined,
        headlines_top_n: topN
      })
      setWorkflowRun(data || null)
      message.success(
        `流程完成：run_id=${data?.run_id || '-'}，导出 ${data?.bridge_run?.export_count || 0} 条`
      )
      await Promise.all([
        loadHeadlines(hours, topN),
        loadBridgePreview(bridgeLimit),
        loadBridgeStatus(),
        loadEngineHealth(projectId),
        loadEngineSnapshot(projectId),
        loadActiveModelProfile(projectId)
      ])
    } catch (error) {
      message.error(`执行统一流程失败: ${error.message}`)
    } finally {
      setRunningWorkflow(false)
    }
  }

  const openEventDetail = async (record) => {
    try {
      const detail = await openspgDemoService.getHeadlineDetail(record.event_id, {
        hours,
        allow_demo_fallback: false
      })
      setSelectedEvent(detail)
      setDrawerOpen(true)
    } catch (error) {
      message.error(`加载事件详情失败: ${error.message}`)
    }
  }

  useEffect(() => {
    loadHeadlines()
    loadEngineSnapshot()
    loadEngineHealth()
    loadBridgePreview()
    loadBridgeStatus()
    loadActiveModelProfile()
    loadLatestWorkflowRun()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadActiveModelProfile(projectId)
    loadLatestWorkflowRun(projectId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const headlineColumns = useMemo(
    () => [
      {
        title: '头条事件',
        dataIndex: 'headline_title',
        key: 'headline_title',
        render: (value, record) => (
          <Space size={6} wrap>
            <Button type="link" style={{ padding: 0 }} onClick={() => openEventDetail(record)}>
              {value}
            </Button>
            <Button
              size="small"
              onClick={() => navigate(`/openspg-kag-headlines/events/${encodeURIComponent(record.event_id)}`)}
            >
              详情页
            </Button>
          </Space>
        )
      },
      {
        title: '类型',
        dataIndex: 'event_type',
        key: 'event_type',
        width: 120,
        render: (value, record) => (
          <Tag color={EVENT_TYPE_COLOR[value] || 'default'}>{record.event_type_zh || value}</Tag>
        )
      },
      {
        title: '涉及企业',
        dataIndex: 'companies',
        key: 'companies',
        render: (items = []) => (
          <Space wrap size={[4, 4]}>
            {items.slice(0, 4).map((item) => (
              <Tag key={item}>{item}</Tag>
            ))}
          </Space>
        )
      },
      {
        title: '来源数',
        dataIndex: 'source_count',
        key: 'source_count',
        width: 90
      },
      {
        title: '证据数',
        dataIndex: 'evidence_count',
        key: 'evidence_count',
        width: 90
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
        width: 220,
        render: (value) => (
          <Text type="secondary">{value ? new Date(value).toLocaleString() : '-'}</Text>
        )
      }
    ],
    [hours, navigate]
  )

  const snapshotSections = useMemo(
    () =>
      engineSnapshot
        ? [
            { key: 'schema', label: 'Schema（设计模板 + OpenSPG查询）', data: engineSnapshot.schema },
            { key: 'builder', label: 'Builder（链路模板 + 任务查询）', data: engineSnapshot.builder },
            { key: 'reason', label: 'Reason 查询结果', data: engineSnapshot.reason },
            { key: 'search', label: 'Search 查询结果', data: engineSnapshot.search },
            { key: 'graph', label: 'Graph 查询结果', data: engineSnapshot.graph }
          ]
        : [],
    [engineSnapshot]
  )

  const tabs = [
    {
      key: 'headlines',
      label: (
        <Space>
          <FireOutlined />
          产业头条
        </Space>
      ),
      children: (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="演示目标"
            description="复用 zhilian-robot 实时资讯接入，使用 OpenSPG/KAG 方案进行事件化聚合与头条展示验证；事件详情保留证据追溯。"
          />

          <Card>
            <Space wrap>
              <Text>时间窗口(小时)</Text>
              <Select
                style={{ width: 120 }}
                value={hours}
                onChange={setHours}
                options={[
                  { value: 6, label: '6小时' },
                  { value: 24, label: '24小时' },
                  { value: 48, label: '48小时' },
                  { value: 72, label: '72小时' }
                ]}
              />
              <Text>TopN</Text>
              <InputNumber min={5} max={100} step={5} value={topN} onChange={(v) => setTopN(v || 20)} />
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                loading={loadingHeadlines}
                onClick={() => loadHeadlines(hours, topN)}
              >
                刷新头条
              </Button>
              <Tag color="processing">数据源: {headlinesData?.meta?.data_source || 'unknown'}</Tag>
            </Space>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card>
                <Statistic title="窗口内资讯（原始输入）" value={headlinesData?.stats?.news_count || 0} />
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card>
                <Statistic title="识别事件数" value={headlinesData?.stats?.event_count || 0} />
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card>
                <Statistic
                  title="多源确认事件"
                  value={headlinesData?.stats?.multi_source_events_count || 0}
                  prefix={<ThunderboltOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Card title="产业头条榜（事件聚合）" extra={<Tag>半实时演示</Tag>}>
            <Table
              rowKey="event_id"
              loading={loadingHeadlines}
              columns={headlineColumns}
              dataSource={headlinesData?.headlines || []}
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: <Empty description="暂无头条事件" /> }}
            />
          </Card>
        </Space>
      )
    },
    {
      key: 'engine',
      label: (
        <Space>
          <ApiOutlined />
          OpenSPG引擎演示
        </Space>
      ),
      children: (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            type="success"
            showIcon
            message="引擎能力演示视图"
            description="展示 OpenSPG Schema/Builder 设计模板，并尝试读取 OpenSPG 的 Reason/Search/Graph 接口结果；服务不可达时自动回退演示数据。"
          />
          <Card>
            <Space wrap>
              <Text>OpenSPG Project ID</Text>
              <InputNumber min={1} value={projectId} onChange={(v) => setProjectId(v || 1)} />
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={() => {
                  loadEngineSnapshot(projectId)
                  loadEngineHealth(projectId)
                }}
                loading={loadingSnapshot}
              >
                刷新引擎快照
              </Button>
              <Button icon={<ReloadOutlined />} onClick={() => loadEngineHealth(projectId)} loading={loadingEngineHealth}>
                刷新健康状态
              </Button>
              <Tag color="purple">
                base_url: {engineSnapshot?.meta?.openspg_base_url || 'http://127.0.0.1:8887'}
              </Tag>
              <Button onClick={() => navigate('/openspg-model-studio')} icon={<BuildOutlined />}>
                打开模型管理
              </Button>
            </Space>
          </Card>

          <Card
            title="统一资讯流程（B方案）"
            extra={<Tag color={workflowRun?.status === 'success' ? 'success' : workflowRun?.status === 'failed' ? 'red' : 'default'}>
              {workflowRun?.status || '未执行'}
            </Tag>}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space wrap>
                {activeModelProfile?.model_profile_id ? (
                  <>
                    <Tag color="processing">激活模型: {activeModelProfile.model_profile_id}</Tag>
                    <Tag color="blue">schema_hash: {activeModelProfile.schema_hash}</Tag>
                  </>
                ) : (
                  <Tag color="gold">当前项目尚未激活模型（将自动回退默认模型）</Tag>
                )}
                <Button icon={<ReloadOutlined />} onClick={() => loadActiveModelProfile(projectId)}>
                  刷新激活模型
                </Button>
                <Button icon={<ReloadOutlined />} onClick={() => loadLatestWorkflowRun(projectId)}>
                  刷新最近流程
                </Button>
              </Space>
              <Space wrap>
                <Button type="primary" loading={runningWorkflow} onClick={runNewsWorkflowByActiveModel}>
                  按激活模型执行统一流程
                </Button>
                {workflowRun?.run_id && <Tag>run_id: {workflowRun.run_id}</Tag>}
                {workflowRun?.bridge_run?.export_count !== undefined && (
                  <Tag color="cyan">导出: {workflowRun.bridge_run.export_count}</Tag>
                )}
                {workflowRun?.builder_submit_result?.mode && (
                  <Tag color="geekblue">Builder: {workflowRun.builder_submit_result.mode}</Tag>
                )}
              </Space>
            </Space>
          </Card>

          <Card
            title="实时资讯接入（zhilian-robot RSS）"
            extra={<Tag color="processing">全真实闭环入口</Tag>}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space wrap>
                <Text>时间窗口(小时)</Text>
                <InputNumber min={1} max={168} value={ingestHours} onChange={(v) => setIngestHours(v || 24)} />
                <Text>每源条数</Text>
                <InputNumber min={1} max={50} value={ingestMaxEntries} onChange={(v) => setIngestMaxEntries(v || 5)} />
                <Button loading={loadingIngest} onClick={pullRealRss} icon={<ReloadOutlined />}>
                  拉取实时资讯
                </Button>
                <Button type="primary" loading={runningRealLoop} onClick={runFullRealLoop}>
                  一键执行全真实闭环
                </Button>
              </Space>
              {ingestResult && (
                <Space wrap>
                  <Tag color="success">拉取 {ingestResult.fetched_count || 0} 条</Tag>
                  <Tag color="blue">新增 {ingestResult.inserted_count || 0} 条</Tag>
                  <Tag>去重 {ingestResult.duplicate_count || 0} 条</Tag>
                </Space>
              )}
            </Space>
          </Card>

          <Card
            title="OpenSPG 实时接入状态"
            extra={
              <Tag color={engineHealth?.status === 'live' ? 'success' : engineHealth?.status === 'partial' ? 'warning' : 'default'}>
                {engineHealth?.status || 'unknown'}
              </Tag>
            }
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Alert
                type={engineHealth?.status === 'live' ? 'success' : engineHealth?.status === 'partial' ? 'warning' : 'info'}
                showIcon
                message={
                  engineHealth
                    ? `OpenSPG ${engineHealth.status === 'live' ? '在线' : engineHealth.status === 'partial' ? '部分可用' : '离线/回退'}`
                    : '尚未加载引擎健康状态'
                }
                description={
                  engineHealth
                    ? `健康检查 ${engineHealth.ok_count || 0}/${engineHealth.total_checks || 0}，Project ID=${engineHealth.project_id}`
                    : '点击“刷新健康状态”获取实时探测结果'
                }
              />
              {engineHealth?.builder_submit_enabled === false && (
                <Alert
                  type="warning"
                  showIcon
                  message="Builder 自动提交已关闭"
                  description={engineHealth?.builder_submit_hint || '需先完成 OpenSPG 计算引擎配置后再启用。'}
                />
              )}
              <Row gutter={[12, 12]}>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="通过检查" value={engineHealth?.ok_count || 0} />
                  </Card>
                </Col>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="总检查项" value={engineHealth?.total_checks || 0} />
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card size="small">
                    <Text type="secondary">OpenSPG Base URL</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag color="purple">{engineHealth?.openspg_base_url || 'http://127.0.0.1:8887'}</Tag>
                    </div>
                  </Card>
                </Col>
              </Row>
              <Space wrap size={[6, 6]}>
                {Object.entries(engineHealth?.checks || {}).map(([name, check]) => (
                  <Tag key={name} color={check?.mode === 'live' && (check?.http_status || 0) < 400 ? 'success' : 'default'}>
                    {name}: {check?.mode || 'n/a'} {check?.http_status ? `(${check.http_status})` : ''}
                  </Tag>
                ))}
              </Space>
            </Space>
          </Card>

          <Card
            title="Builder 输入批次（zhilian-robot -> OpenSPG 桥接预览）"
            extra={<Tag color="cyan">{bridgePreview?.meta?.data_source || 'unknown'}</Tag>}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space wrap>
                <Text>导出条数</Text>
                <InputNumber
                  min={10}
                  max={500}
                  step={10}
                  value={bridgeLimit}
                  onChange={(v) => setBridgeLimit(v || 50)}
                />
                <Button
                  icon={<ReloadOutlined />}
                  loading={loadingBridgePreview}
                  onClick={() => loadBridgePreview(bridgeLimit)}
                >
                  刷新预览
                </Button>
                <Button
                  type="primary"
                  onClick={() => {
                    const url = openspgDemoService.getBridgeExportUrl({ limit: bridgeLimit })
                    window.open(url, '_blank', 'noopener,noreferrer')
                  }}
                >
                  下载 JSONL 批次
                </Button>
                <Checkbox checked={bridgeSubmitBuilder} onChange={(e) => setBridgeSubmitBuilder(e.target.checked)}>
                  桥接后提交 Builder 任务并执行真实导入（默认开启）
                </Checkbox>
                <Input
                  style={{ minWidth: 360 }}
                  placeholder="可选：Builder command（未填则使用后端默认命令）"
                  value={bridgeCommand}
                  onChange={(e) => setBridgeCommand(e.target.value)}
                />
                <Button
                  type="primary"
                  loading={runningBridge}
                  onClick={() => triggerBridgeRun({ forceFull: false, submitBuilder: bridgeSubmitBuilder })}
                >
                  触发增量桥接
                </Button>
                <Button loading={runningBridge} onClick={() => triggerBridgeRun({ forceFull: true, submitBuilder: bridgeSubmitBuilder })}>
                  触发全量桥接
                </Button>
                <Button icon={<ReloadOutlined />} loading={loadingBridgeStatus} onClick={loadBridgeStatus}>
                  刷新桥接状态
                </Button>
              </Space>

              <Card size="small" title="桥接运行状态（半实时闭环）">
                <Row gutter={[12, 12]}>
                  <Col xs={24} md={8}>
                    <Card size="small">
                      <Statistic title="最近导出条数" value={bridgeStatus?.last_run?.export_count || 0} />
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card size="small">
                      <Statistic title="最近输入条数" value={bridgeStatus?.last_run?.input_count || 0} />
                    </Card>
                  </Col>
                  <Col xs={24} md={8}>
                    <Card size="small">
                      <Statistic title="最近批次数（保留）" value={(bridgeStatus?.recent_runs || []).length} />
                    </Card>
                  </Col>
                </Row>

                <Space direction="vertical" size={8} style={{ width: '100%', marginTop: 12 }}>
                  <Space wrap>
                    <Tag color="processing">数据源: {bridgeStatus?.meta?.data_source || 'unknown'}</Tag>
                    <Tag color="blue">
                      游标: {bridgeStatus?.cursor?.last_seen_time ? new Date(bridgeStatus.cursor.last_seen_time).toLocaleString() : '未建立'}
                    </Tag>
                    {bridgeStatus?.last_run?.run_id && (
                      <Button
                        size="small"
                        onClick={() => {
                          const url = openspgDemoService.getBridgeRunDownloadUrl(bridgeStatus.last_run.run_id)
                          window.open(url, '_blank', 'noopener,noreferrer')
                        }}
                      >
                        下载最近批次
                      </Button>
                    )}
                  </Space>

                  {(bridgeStatus?.recent_runs || []).length > 0 ? (
                    <Timeline
                      items={(bridgeStatus?.recent_runs || []).slice(0, 5).map((run) => ({
                        color: 'blue',
                        children: (
                          <Space wrap>
                            <Text>{run.run_id}</Text>
                            <Tag>{run.export_count} 条</Tag>
                            <Tag>{run.force_full ? '全量' : '增量'}</Tag>
                            {run.batch_file_name && <Text type="secondary">{run.batch_file_name}</Text>}
                          </Space>
                        )
                      }))}
                    />
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无桥接运行记录" />
                  )}
                </Space>
              </Card>

              <Row gutter={[12, 12]}>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="批次记录数" value={bridgePreview?.meta?.row_count || 0} />
                  </Card>
                </Col>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="JSONL行数" value={bridgePreview?.meta?.jsonl_line_count || 0} />
                  </Card>
                </Col>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="来源数" value={bridgePreview?.stats?.unique_sources || 0} />
                  </Card>
                </Col>
                <Col xs={24} md={6}>
                  <Card size="small">
                    <Statistic title="样例预览行" value={bridgePreview?.meta?.sample_lines || 0} />
                  </Card>
                </Col>
              </Row>

              <Space wrap size={[6, 6]}>
                {(bridgePreview?.stats?.source_distribution || []).slice(0, 8).map((item) => (
                  <Tag key={item.source_name}>
                    {item.source_name}: {item.count}
                  </Tag>
                ))}
              </Space>

              <Row gutter={[16, 16]}>
                <Col xs={24} xl={12}>
                  <JsonPanel
                    title="标准化记录样例（Builder 输入对象）"
                    data={bridgePreview?.sample_records}
                    extra={<Tag>{bridgePreview?.meta?.row_count || 0} records</Tag>}
                    height={260}
                  />
                </Col>
                <Col xs={24} xl={12}>
                  <Card title="JSONL 预览（可直接供 Builder 消费）" size="small">
                    <pre
                      style={{
                        margin: 0,
                        maxHeight: 260,
                        overflow: 'auto',
                        background: '#020617',
                        color: '#cbd5e1',
                        padding: 12,
                        borderRadius: 8,
                        border: '1px solid #334155',
                        fontSize: 12,
                        lineHeight: 1.45,
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all'
                      }}
                    >
                      {(bridgePreview?.jsonl_preview || []).join('\n') || '暂无预览'}
                    </pre>
                  </Card>
                </Col>
              </Row>
            </Space>
          </Card>

          <Spin spinning={loadingSnapshot}>
            <Row gutter={[16, 16]}>
              <Col xs={24} xl={12}>
                <JsonPanel
                  title="Schema 模板（机器人主链MVP）"
                  data={engineSnapshot?.schema?.template}
                  extra={<Tag color="blue">{engineSnapshot?.schema?.live_query?.mode || 'template'}</Tag>}
                  height={360}
                />
              </Col>
              <Col xs={24} xl={12}>
                <JsonPanel
                  title="BuilderChain 模板（KAG 风格）"
                  data={engineSnapshot?.builder?.template}
                  extra={<Tag color="geekblue">{engineSnapshot?.builder?.live_query?.mode || 'template'}</Tag>}
                  height={360}
                />
              </Col>
            </Row>

            <Card title="OpenSPG 接口返回（Reason / Search / Graph）">
              <Collapse
                items={snapshotSections.map((section) => ({
                  key: section.key,
                  label: section.label,
                  children: (
                    <JsonPanel
                      title={`${section.key.toUpperCase()} 返回`}
                      data={section.data}
                      extra={<Tag>{section.data?.mode || section.data?.live_query?.mode || 'n/a'}</Tag>}
                      height={260}
                    />
                  )
                }))}
              />
            </Card>
          </Spin>
        </Space>
      )
    }
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          <PartitionOutlined style={{ marginRight: 8 }} />
          OpenSPG/KAG 产业头条演示
        </Title>
        <Text type="secondary">
          业务展示放在 zhilian-robot 前端，OpenSPG 侧展示 Schema、Builder任务与 Reason/Search/Graph 查询结果（引擎能力证明）。
        </Text>
      </div>

      <Tabs defaultActiveKey="headlines" items={tabs} />

      <Drawer
        title={selectedEvent?.event_title || '事件详情'}
        open={drawerOpen}
        width={720}
        onClose={() => setDrawerOpen(false)}
      >
        {!selectedEvent ? (
          <Spin />
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Card size="small">
              <Descriptions column={2} size="small" bordered>
                <Descriptions.Item label="事件类型">
                  <Tag color={EVENT_TYPE_COLOR[selectedEvent.event_type] || 'default'}>
                    {selectedEvent.event_type_zh || selectedEvent.event_type}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="头条分">
                  {selectedEvent.headline_score}
                </Descriptions.Item>
                <Descriptions.Item label="来源数">
                  {selectedEvent.source_count}
                </Descriptions.Item>
                <Descriptions.Item label="涉及企业">
                  <Space wrap>
                    {(selectedEvent.companies || []).map((c) => (
                      <Tag key={c}>{c}</Tag>
                    ))}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="首次时间">
                  {selectedEvent.first_publish_time ? new Date(selectedEvent.first_publish_time).toLocaleString() : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="最新时间">
                  {selectedEvent.latest_publish_time ? new Date(selectedEvent.latest_publish_time).toLocaleString() : '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="证据新闻（可追溯）" size="small">
              <Table
                rowKey="news_id"
                size="small"
                pagination={false}
                dataSource={selectedEvent.evidence_news || []}
                columns={[
                  {
                    title: '标题',
                    dataIndex: 'title',
                    render: (value, row) => (
                      <a href={row.url} target="_blank" rel="noreferrer">
                        {value}
                      </a>
                    )
                  },
                  { title: '来源', dataIndex: 'source_name', width: 120 },
                  {
                    title: '证据片段',
                    dataIndex: 'snippet',
                    ellipsis: true,
                    render: (value) => <Text type="secondary">{value || '-'}</Text>
                  },
                  {
                    title: '时间',
                    dataIndex: 'publish_time',
                    width: 180,
                    render: (v) => (v ? new Date(v).toLocaleString() : '-')
                  }
                ]}
              />
            </Card>

            <JsonPanel title="事件原始数据(JSON)" data={selectedEvent} height={240} />
          </Space>
        )}
      </Drawer>
    </div>
  )
}

export default OpenSPGKagHeadlinesPage
