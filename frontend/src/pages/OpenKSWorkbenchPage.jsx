import React, { useEffect, useMemo, useState } from 'react'
import { App as AntdApp, Alert, Button, Card, Empty, Segmented, Space, Spin, Table, Tag, Typography } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { DatabaseOutlined, ApartmentOutlined, DeploymentUnitOutlined, FileSearchOutlined, NodeIndexOutlined, ReloadOutlined } from '@ant-design/icons'
import { OPENKS_WORKBENCH_BLOCKS, getOpenksWorkbenchBlockByKey } from './openksWorkbenchModel.mjs'
import { openksWorkbenchApi } from '../services/openksWorkbenchApi'
import { getOpenksPortalUrl } from '../utils/openksPortal'

const { Title, Paragraph, Text } = Typography

const RUNTIME_PROFILE = 'kag_openspg'

const iconMap = {
  overview: <DeploymentUnitOutlined />,
  schema: <DatabaseOutlined />,
  modules: <ApartmentOutlined />,
  chain: <NodeIndexOutlined />,
  results: <FileSearchOutlined />,
}

const STEP_CONFIG = {
  schema_sync: {
    label: 'Schema Sync',
    buttonLabel: '执行 Schema Sync',
    detailKey: 'model',
    runApi: 'runWorkflowModel',
    buildPayload: () => ({
      project_id: 1,
      activate_label: 'openks-workbench',
    }),
  },
  bridge_export: {
    label: 'Extract',
    buttonLabel: '执行 Extract',
    detailKey: 'extract',
    runApi: 'runWorkflowExtract',
    buildPayload: () => ({
      project_id: 1,
      limit: 200,
      force_full: true,
      use_active_model: true,
      worker_num: 1,
      runtime_profile: RUNTIME_PROFILE,
    }),
  },
  graph_materialize: {
    label: 'Execute',
    buttonLabel: '执行 Execute',
    detailKey: 'execute',
    runApi: 'runWorkflowExecute',
    buildPayload: () => ({
      project_id: 1,
      worker_num: 1,
      limit: 200,
      runtime_profile: RUNTIME_PROFILE,
    }),
  },
}

function resolveTab(raw) {
  const allowed = ['overview', 'schema', 'modules', 'chain', 'results']
  return allowed.includes(raw) ? raw : 'overview'
}

function latestItem(items = []) {
  return Array.isArray(items) && items.length ? items[0] : null
}

function normalizeStepStatus(value) {
  const text = String(value || '').toLowerCase()
  if (text === 'success' || text === 'completed' || text === 'finish' || text === 'done' || text === 'active' || text === 'ready' || text === 'implemented') {
    return { color: 'green', label: '已完成' }
  }
  if (text === 'running' || text === 'process') {
    return { color: 'blue', label: '执行中' }
  }
  if (text === 'failed' || text === 'error') {
    return { color: 'red', label: '失败' }
  }
  if (text === 'queued' || text === 'pending' || text === 'wait') {
    return { color: 'default', label: '待执行' }
  }
  return { color: 'default', label: '未运行' }
}

function getChainStatus(stepKey, workflowRun, runtimeRun) {
  if (stepKey === 'workflow') {
    return normalizeStepStatus(workflowRun?.status)
  }
  if (stepKey === 'schema_sync') {
    return normalizeStepStatus(workflowRun?.step_statuses?.model?.status)
  }
  if (stepKey === 'bridge_export') {
    return normalizeStepStatus(workflowRun?.step_statuses?.extract?.status)
  }
  if (stepKey === 'graph_materialize') {
    return normalizeStepStatus(workflowRun?.step_statuses?.execute?.status)
  }
  if (stepKey === 'runtime_binding') {
    return normalizeStepStatus(runtimeRun?.status || workflowRun?.runtime_binding?.run?.status)
  }
  return normalizeStepStatus('')
}

function stringifyPayload(payload) {
  return JSON.stringify(payload ?? {}, null, 2)
}

const WorkbenchStat = ({ label, value, accent = '' }) => (
  <div className="openks-stat-block">
    <Text className="openks-stat-label">{label}</Text>
    <Title level={4} className="openks-stat-value">
      {value}
    </Title>
    {accent ? <Text className="openks-stat-accent">{accent}</Text> : null}
  </div>
)

const BulletList = ({ items = [] }) => (
  <div className="openks-bullet-list">
    {items.map((item) => (
      <div key={item} className="openks-bullet-item">
        <span className="openks-bullet-dot" />
        <Text>{item}</Text>
      </div>
    ))}
  </div>
)

const InsightCard = ({ eyebrow, title, summary, bullets = [], chips = [], tag = '' }) => (
  <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
    <div className="openks-overview-card-head">
      <div>
        <Text className="openks-panel-eyebrow">{eyebrow}</Text>
        <Title level={4} style={{ margin: '6px 0 0' }}>{title}</Title>
      </div>
      {tag ? <Tag color="blue">{tag}</Tag> : null}
    </div>
    <Paragraph style={{ marginBottom: 12 }}>{summary}</Paragraph>
    {chips.length ? (
      <div className="openks-chip-row" style={{ marginBottom: 12 }}>
        {chips.map((item) => (
          <span key={item} className="openks-chip">{item}</span>
        ))}
      </div>
    ) : null}
    <BulletList items={bullets} />
  </Card>
)

const ProductionStepCard = ({ step, status }) => (
  <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
    <div className="openks-overview-card-head">
      <div>
        <Text className="openks-panel-eyebrow">主链步骤</Text>
        <Title level={4} style={{ margin: '6px 0 0' }}>{step.title}</Title>
      </div>
      <Tag color={status.color}>{status.label}</Tag>
    </div>
    <Text className="openks-step-endpoint">{step.run_api}</Text>
    <Paragraph style={{ margin: '10px 0 12px' }}>{step.function_entry}</Paragraph>
    <Text className="openks-panel-eyebrow">输入</Text>
    <div className="openks-chip-row" style={{ margin: '8px 0 12px' }}>
      {(step.input_fields || []).map((item) => (
        <span key={item} className="openks-chip">{item}</span>
      ))}
    </div>
    <Text className="openks-panel-eyebrow">输出</Text>
    <div className="openks-chip-row" style={{ marginTop: 8 }}>
      {(step.output_fields || []).map((item) => (
        <span key={item} className="openks-chip accent">{item}</span>
      ))}
    </div>
  </Card>
)

const JsonBlock = ({ title, payload }) => (
  <Card className="openks-panel-card" bodyStyle={{ padding: 20 }}>
    <Text className="openks-panel-eyebrow">{title}</Text>
    <pre className="openks-json-block">{stringifyPayload(payload)}</pre>
  </Card>
)

const OpenKSWorkbenchPage = () => {
  const [searchParams] = useSearchParams()
  const { message } = AntdApp.useApp()
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState(null)
  const [modules, setModules] = useState([])
  const [workflowLatest, setWorkflowLatest] = useState(null)
  const [runtimeRuns, setRuntimeRuns] = useState([])
  const [runtimeArtifacts, setRuntimeArtifacts] = useState([])
  const [runtimeReleases, setRuntimeReleases] = useState([])
  const [stepSnapshots, setStepSnapshots] = useState({})
  const [selectedDetailKey, setSelectedDetailKey] = useState('schema_sync')
  const [runningStepKey, setRunningStepKey] = useState('')
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')

  const activeTab = resolveTab(searchParams.get('tab'))
  const activeBlock = useMemo(() => {
    if (activeTab === 'overview') return getOpenksWorkbenchBlockByKey('production-chain')
    if (activeTab === 'chain') return getOpenksWorkbenchBlockByKey('production-chain')
    if (activeTab === 'results') return getOpenksWorkbenchBlockByKey('graph-results')
    return getOpenksWorkbenchBlockByKey(activeTab)
  }, [activeTab])

  const loadProductionData = async () => {
    setLoading(true)
    setError('')

    const settled = await Promise.allSettled([
      openksWorkbenchApi.getOverview(),
      openksWorkbenchApi.getModules(),
      openksWorkbenchApi.getWorkflowLatest(1),
      openksWorkbenchApi.getRuntimeRuns({ kg_name: 'news_kg', runtime_profile: RUNTIME_PROFILE, limit: 6 }),
      openksWorkbenchApi.getRuntimeArtifacts({ kg_name: 'news_kg', runtime_profile: RUNTIME_PROFILE, limit: 6 }),
      openksWorkbenchApi.getRuntimeReleases({ kg_name: 'news_kg', runtime_profile: RUNTIME_PROFILE, limit: 6 }),
    ])

    const [overviewResult, modulesResult, workflowResult, runsResult, artifactsResult, releasesResult] = settled
    const unwrap = (result, fallback) => (result.status === 'fulfilled' ? result.value : fallback)

    setOverview(unwrap(overviewResult, null))
    setModules(unwrap(modulesResult, { modules: [] })?.modules || [])
    setWorkflowLatest(unwrap(workflowResult, null))
    setRuntimeRuns(unwrap(runsResult, { items: [] })?.items || [])
    setRuntimeArtifacts(unwrap(artifactsResult, { items: [] })?.items || [])
    setRuntimeReleases(unwrap(releasesResult, { items: [] })?.items || [])

    if (settled.some((item) => item.status === 'rejected')) {
      setError('部分生产主链数据加载失败，页面已按可用数据降级展示。')
    }
    setLoading(false)
  }

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      await loadProductionData()
      if (cancelled) return
    }

    run()
    return () => {
      cancelled = true
    }
  }, [])

  const latestRun = latestItem(runtimeRuns)
  const latestArtifact = latestItem(runtimeArtifacts)
  const latestRelease = latestItem(runtimeReleases)
  const mainChain = overview?.main_chain || {}
  const integrationBoundary = overview?.integration_boundary || {}
  const governance = overview?.industry_graph_governance || {}
  const productionSteps = overview?.production_steps || []
  const openksPageRequirements = overview?.openks_page_requirements || []
  const openksPortalUrl = getOpenksPortalUrl('/')

  const loadStepDetail = async (stepKey) => {
    const stepConfig = STEP_CONFIG[stepKey]
    const runId = workflowLatest?.run_id
    if (!stepConfig || !runId) {
      message.info('暂无可读取的 workflow run，请先执行对应生产步骤。')
      return
    }

    setDetailLoading(true)
    try {
      const detail = await openksWorkbenchApi.getWorkflowStepDetail(runId, stepConfig.detailKey)
      setStepSnapshots((previous) => ({
        ...previous,
        [stepKey]: {
          source: 'workflow-step-detail',
          run_id: runId,
          fetched_at: new Date().toISOString(),
          input: {
            run_id: runId,
            step_key: stepConfig.detailKey,
          },
          output: detail,
        },
      }))
    } catch (nextError) {
      message.warning(nextError.message || 'Step Detail 读取失败')
    } finally {
      setDetailLoading(false)
    }
  }

  const runWorkflowStep = async (stepKey) => {
    const stepConfig = STEP_CONFIG[stepKey]
    if (!stepConfig) return

    const payload = stepConfig.buildPayload()
    setRunningStepKey(stepKey)
    try {
      const result = await openksWorkbenchApi[stepConfig.runApi](payload)
      setStepSnapshots((previous) => ({
        ...previous,
        [stepKey]: {
          source: 'openks-manual-run',
          fetched_at: new Date().toISOString(),
          input: payload,
          output: result,
        },
      }))
      setSelectedDetailKey(stepKey)
      await loadProductionData()
      message.success(`${stepConfig.buttonLabel} 已触发`)
    } catch (nextError) {
      message.error(nextError.message || `${stepConfig.buttonLabel} 失败`)
    } finally {
      setRunningStepKey('')
    }
  }

  const selectedSnapshot = stepSnapshots[selectedDetailKey] || null

  const overviewPanel = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <div className="openks-panel-grid">
        <div className="openks-panel-feature">
          <Space direction="vertical" size={12}>
            <Text className="openks-panel-eyebrow">运行主线</Text>
            <Title level={3} style={{ margin: 0 }}>
              {'Workflow -> Schema Sync -> Bridge Export -> OpenSPG Upsert -> Runtime Binding'}
            </Title>
            <Paragraph style={{ margin: 0 }}>
              工作台不再展示合同化 `build-jobs`。当前只承认 `kag_openspg` 这条正式生产链，并用 workflow、runtime runs、artifacts、releases 来组织状态与结果。
            </Paragraph>
            <div className="openks-chip-row">
              {[
                `独立域名: ${openksPortalUrl}`,
                `主链: ${mainChain.runtime_profile || RUNTIME_PROFILE}`,
                `状态: ${mainChain.status || 'production'}`,
              ].map((item) => (
                <span key={item} className="openks-chip accent">{item}</span>
              ))}
            </div>
          </Space>
        </div>
        <div className="openks-panel-stats">
          <WorkbenchStat label="最新 Workflow" value={workflowLatest?.run_id || '—'} accent={workflowLatest?.status || '未运行'} />
          <WorkbenchStat label="最新 Run" value={latestRun?.run_id || '—'} accent={latestRun?.status || '未绑定'} />
          <WorkbenchStat label="最新 Artifact" value={latestArtifact?.artifact_id || '—'} accent={latestArtifact?.status || '未生成'} />
          <WorkbenchStat label="最新 Release" value={latestRelease?.release_id || '—'} accent={latestRelease?.status || '未发布'} />
        </div>
      </div>

      <div className="openks-overview-grid">
        <InsightCard
          eyebrow="DataHub 接口规范"
          title={integrationBoundary?.datahub?.headlines_endpoint || 'GET /api/v1/datahub/mock/headlines'}
          summary="DataHub 真实对接先不做，但合同、字段和 OpenKS 提交口径已经先固定，前端可直接拿 mock 头条接口联调。"
          chips={['doc_id', 'title', 'summary', 'content', 'source_name', 'source_url', 'publish_time']}
          bullets={integrationBoundary?.datahub?.notes || []}
          tag="mock 已就绪"
        />
        <InsightCard
          eyebrow="Graphiti 接入说明"
          title={integrationBoundary?.graphiti?.required_endpoint || 'POST /messages'}
          summary="Graphiti 暂不接真实服务，当前只保留兼容真实契约的适配层，明确 group_id、message 与事件包字段。"
          chips={integrationBoundary?.graphiti?.required_fields || []}
          bullets={integrationBoundary?.graphiti?.notes || []}
          tag="合同占位"
        />
        <InsightCard
          eyebrow="OpenSPG 主生产链"
          title={mainChain.runtime_profile || RUNTIME_PROFILE}
          summary={mainChain.description || 'OpenSPG 负责内部主存与图服务，OpenKS 负责 schema、知识计算与运行时绑定。'}
          chips={['workflow', 'schema sync', 'bridge export', 'upsertVertex', 'upsertEdge', 'runtime binding']}
          bullets={productionSteps.map((item) => `${item.title} -> ${item.function_entry}`)}
          tag={mainChain.status || 'production'}
        />
        <InsightCard
          eyebrow="图谱审核"
          title="产业网图谱审核与优化"
          summary="当前产业网图谱还是以资讯事件聚合和生产主链 runtime 结果为主，必须通过证据回溯、抽样复核和坏样本沉淀来保证正确性。"
          chips={governance?.openspg_capabilities || []}
          bullets={governance?.audit_checks || []}
          tag="可审计"
        />
      </div>
    </Space>
  )

  const schemaPanel = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Schema 概览</Text>
        <Title level={3} style={{ marginTop: 6 }}>IncCore.schema 子集启用</Title>
        <Paragraph>
          当前以 `Document / Chunk / DataSource / Company / Technology / Event` 为第一阶段主 schema 子集，后续逐步扩展企业库与链图专题。
        </Paragraph>
        <div className="openks-chip-row">
          {['Document', 'Chunk', 'DataSource', 'Company', 'Technology', 'Event', 'CompanyCooperationEvent'].map((item) => (
            <span key={item} className="openks-chip">{item}</span>
          ))}
        </div>
      </Card>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Schema 结构说明</Text>
        <BulletList items={OPENKS_WORKBENCH_BLOCKS[0].items} />
      </Card>
    </Space>
  )

  const modulesPanel = modules.length ? (
    <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
      <Text className="openks-panel-eyebrow">KG 模块状态</Text>
      <Table
        size="small"
        pagination={false}
        rowKey="name"
        dataSource={modules}
        columns={[
          { title: '模块', dataIndex: 'title', key: 'title' },
          { title: '代码名', dataIndex: 'name', key: 'name' },
          { title: '阶段', dataIndex: 'stage', key: 'stage' },
          {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            render: (value) => <Tag color={normalizeStepStatus(value).color}>{value}</Tag>,
          },
          {
            title: '能力',
            key: 'flags',
            render: (_, record) => (
              <Space size={[4, 4]} wrap>
                {record.has_schema ? <Tag>schema</Tag> : null}
                {record.has_builder ? <Tag>builder</Tag> : null}
                {record.has_reasoner ? <Tag>reasoner</Tag> : null}
                {record.has_solver ? <Tag>solver</Tag> : null}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  ) : <Empty description="暂无模块数据" />

  const chainPanel = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <div className="openks-overview-card-head">
          <div>
            <Text className="openks-panel-eyebrow">主链运行</Text>
            <Title level={3} style={{ margin: '6px 0 0' }}>生产主链操作按钮</Title>
          </div>
          <Button icon={<ReloadOutlined />} onClick={loadProductionData}>刷新生产状态</Button>
        </div>
        <Paragraph style={{ marginBottom: 12 }}>
          这里直接挂的是生产主链步骤接口：`/workflow/news/steps/model|extract|execute`。点击后会把本次请求和返回写入当前页面的 Step Detail。
        </Paragraph>
        <Space wrap size={12}>
          {Object.entries(STEP_CONFIG).map(([stepKey, config]) => (
            <Button
              key={stepKey}
              type="primary"
              onClick={() => runWorkflowStep(stepKey)}
              loading={runningStepKey === stepKey}
            >
              {config.buttonLabel}
            </Button>
          ))}
        </Space>
      </Card>

      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <div className="openks-overview-card-head">
          <div>
            <Text className="openks-panel-eyebrow">生产主链</Text>
            <Title level={3} style={{ margin: '6px 0 0' }}>主链步骤与接口定义</Title>
          </div>
          <Tag color="green">{mainChain.status || 'production'}</Tag>
        </div>
        <Paragraph style={{ marginBottom: 12 }}>
          下面这 5 步就是当前 OpenKS 页面应该承认和展示的正式生产链。每一步都明确了运行接口、核心方法、输入和输出。
        </Paragraph>
        <div className="openks-overview-grid">
          {productionSteps.map((step) => (
            <ProductionStepCard
              key={step.key}
              step={step}
              status={getChainStatus(step.key, workflowLatest, latestRun)}
            />
          ))}
        </div>
      </Card>

      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <div className="openks-overview-card-head">
          <div>
            <Text className="openks-panel-eyebrow">Step Detail</Text>
            <Title level={3} style={{ margin: '6px 0 0' }}>输入 / 输出快照</Title>
          </div>
          <Button icon={<ReloadOutlined />} loading={detailLoading} onClick={() => loadStepDetail(selectedDetailKey)}>
            刷新 Step Detail
          </Button>
        </div>
        <Paragraph style={{ marginBottom: 12 }}>
          这里优先展示你在 OpenKS 页面点击按钮后产生的实时输入/输出快照；如果已有 `workflow latest`，也可以从后端 step detail 接口回拉。
        </Paragraph>
        <Segmented
          value={selectedDetailKey}
          onChange={setSelectedDetailKey}
          options={Object.entries(STEP_CONFIG).map(([stepKey, config]) => ({
            label: config.label,
            value: stepKey,
          }))}
          style={{ marginBottom: 16 }}
        />
        {selectedSnapshot ? (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color="processing">source: {selectedSnapshot.source || 'manual'}</Tag>
              {selectedSnapshot.run_id ? <Tag>run_id: {selectedSnapshot.run_id}</Tag> : null}
              <Tag>{selectedSnapshot.fetched_at || 'now'}</Tag>
            </Space>
            <div className="openks-json-grid">
              <JsonBlock title="输入快照" payload={selectedSnapshot.input} />
              <JsonBlock title="输出快照" payload={selectedSnapshot.output} />
            </div>
          </Space>
        ) : (
          <Empty description="暂无 Step Detail。先点击执行按钮，或在有最新 workflow run 后点击刷新。" />
        )}
      </Card>

      <InsightCard
        eyebrow="页面运行缺口"
        title="如果要在 OpenKS 页面直接运行和展示，还需要什么"
        summary="定义已经基本明确，但要把运行能力真正前置到 OpenKS 页面，还需要把 workflow step 入口、step detail 快照和 runtime 结果读取彻底绑到同一条生产主线上。"
        bullets={openksPageRequirements}
        chips={['workflow buttons', 'step detail', 'artifact_id', 'retry/logging', 'auth']}
        tag="待补齐"
      />
    </Space>
  )

  const resultsPanel = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Production Runtime 摘要</Text>
        <div className="openks-panel-stats openks-panel-stats-tight">
          <WorkbenchStat label="实体数" value={latestArtifact?.entity_count ?? '—'} />
          <WorkbenchStat label="关系数" value={latestArtifact?.statement_count ?? '—'} />
          <WorkbenchStat label="上下文数" value={latestArtifact?.context_count ?? '—'} />
          <WorkbenchStat label="Release" value={latestRelease?.status || '—'} />
        </div>
      </Card>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Runs</Text>
        <Table
          size="small"
          pagination={false}
          rowKey="run_id"
          dataSource={runtimeRuns.slice(0, 6)}
          columns={[
            { title: 'Run', dataIndex: 'run_id', key: 'run_id' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (value) => <Tag color={normalizeStepStatus(value).color}>{value}</Tag>,
            },
            { title: 'Artifact Ref', dataIndex: 'artifact_ref', key: 'artifact_ref' },
          ]}
        />
      </Card>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Artifacts</Text>
        <Table
          size="small"
          pagination={false}
          rowKey="artifact_id"
          dataSource={runtimeArtifacts.slice(0, 6)}
          columns={[
            { title: 'Artifact', dataIndex: 'artifact_id', key: 'artifact_id' },
            { title: 'Version', dataIndex: 'version', key: 'version' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (value) => <Tag color={normalizeStepStatus(value).color}>{value}</Tag>,
            },
          ]}
        />
      </Card>
      <Card className="openks-panel-card" bodyStyle={{ padding: 24 }}>
        <Text className="openks-panel-eyebrow">Releases</Text>
        <Table
          size="small"
          pagination={false}
          rowKey="release_id"
          dataSource={runtimeReleases.slice(0, 6)}
          columns={[
            { title: 'Release', dataIndex: 'release_id', key: 'release_id' },
            { title: 'Version', dataIndex: 'version', key: 'version' },
            {
              title: '状态',
              dataIndex: 'status',
              key: 'status',
              render: (value) => <Tag color={normalizeStepStatus(value).color}>{value}</Tag>,
            },
          ]}
        />
      </Card>
    </Space>
  )

  const renderActivePanel = () => {
    if (activeTab === 'overview') return overviewPanel
    if (activeTab === 'schema') return schemaPanel
    if (activeTab === 'modules') return modulesPanel
    if (activeTab === 'chain') return chainPanel
    if (activeTab === 'results') return resultsPanel
    return overviewPanel
  }

  return (
    <div className="openks-workbench-page">
      <div className="openks-workbench-hero">
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          <Tag className="openks-workbench-tag">OpenKS 独立产品入口</Tag>
          <div className="openks-workbench-head">
            <div>
              <Text className="openks-panel-eyebrow">当前分区</Text>
              <Title level={1} className="openks-workbench-title">
                {activeTab === 'overview' ? '生产主链总览' : activeBlock.title}
              </Title>
            </div>
            <div className="openks-workbench-head-icon">
              {iconMap[activeTab]}
            </div>
          </div>
          <Paragraph className="openks-workbench-copy">
            OpenKS 已经从中试平台摘要页中拆出来，作为独立部署的知识计算工作台使用。当前页面只展示正式生产链，不再把合同化 `build-jobs` 当作主入口；你现在可以直接在这里触发 `model / extract / execute` 三个生产步骤。
          </Paragraph>
          <div className="openks-chip-row">
            {['独立导航', '生产主链', 'Workflow Runtime', 'Artifacts', 'Releases', 'Step Detail'].map((item) => (
              <span key={item} className="openks-chip accent">{item}</span>
            ))}
          </div>
        </Space>
      </div>

      {error ? <Alert type="warning" message={error} showIcon /> : null}

      {loading ? (
        <Card className="openks-panel-card" bodyStyle={{ padding: 32 }}>
          <Space direction="vertical" size={12} style={{ width: '100%', alignItems: 'center' }}>
            <Spin size="large" />
            <Text>正在加载 OpenKS 工作台生产主链数据...</Text>
          </Space>
        </Card>
      ) : renderActivePanel()}
    </div>
  )
}

export default OpenKSWorkbenchPage
