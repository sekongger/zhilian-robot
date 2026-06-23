import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Row, Space, message } from 'antd'
import { ReloadOutlined, UnorderedListOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import workflowApi from '../services/workflowApi'
import modelStudioApi from '../services/modelStudioApi'
import WorkflowHeader from '../components/workflow/WorkflowHeader'
import GlobalRunControlBar from '../components/workflow/GlobalRunControlBar'
import PipelineStepper from '../components/workflow/PipelineStepper'
import RunHistoryTable from '../components/workflow/RunHistoryTable'
import StepCollectPanel from '../components/workflow/StepCollectPanel'
import StepProcessPanel from '../components/workflow/StepProcessPanel'
import StepExtractPanel from '../components/workflow/StepExtractPanel'
import StepModelPanel from '../components/workflow/StepModelPanel'
import StepExecutePanel from '../components/workflow/StepExecutePanel'
import StepApplyPanel from '../components/workflow/StepApplyPanel'
import StepDetailDrawer from '../components/workflow/StepDetailDrawer'

const ACTIVE_RUN_STATUSES = new Set(['queued', 'running'])
const TERMINAL_RUN_STATUSES = new Set(['success', 'partial_success', 'failed'])

const STEP_DEFS = [
  { key: 'model', title: '建模', desc: 'OpenKS schema 适配与提交' },
  { key: 'collect', title: '采集', desc: 'RSS/API 采集资讯数据' },
  { key: 'process', title: '处理', desc: '标准化与批次准备' },
  { key: 'extract', title: '抽取', desc: 'KAG bridge 导出' },
  { key: 'execute', title: '执行', desc: 'Builder 提交与图物化' },
  { key: 'apply', title: '应用', desc: 'Artifact / Release 消费快照' },
]

const defaultParams = {
  project_id: 1,
  runtime_profile: 'kag_openspg',
  hours_ago: 24,
  max_entries_per_feed: 5,
  bridge_limit: 200,
  force_full: true,
  submit_builder: true,
  apply_schema: true,
  worker_num: 1,
  builder_command: '',
  headlines_top_n: 20,
}

const initialLoading = {
  collect: false,
  process: false,
  model: false,
  extract: false,
  execute: false,
  apply: false,
}

const initialErrors = {
  collect: '',
  process: '',
  model: '',
  extract: '',
  execute: '',
  apply: '',
}

const WorkflowWorkbenchPage = () => {
  const [searchParams] = useSearchParams()
  const [params, setParams] = useState(defaultParams)
  const [schemaScript, setSchemaScript] = useState('')

  const [running, setRunning] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [run, setRun] = useState(null)
  const [history, setHistory] = useState([])

  const [stepLoading, setStepLoading] = useState(initialLoading)
  const [stepErrors, setStepErrors] = useState(initialErrors)
  const [stepResults, setStepResults] = useState({})
  const [submittedRunId, setSubmittedRunId] = useState('')
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false)
  const [detailRunId, setDetailRunId] = useState('')
  const [detailStepKey, setDetailStepKey] = useState('apply')
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailCache, setDetailCache] = useState({})

  const setParam = (key, value) => {
    setParams((prev) => ({ ...prev, [key]: value }))
  }

  const setStepResult = (key, data) => {
    setStepResults((prev) => ({ ...prev, [key]: data }))
    setStepErrors((prev) => ({ ...prev, [key]: '' }))
  }

  const setStepError = (key, error) => {
    setStepErrors((prev) => ({ ...prev, [key]: error }))
  }

  const setLoading = (key, loading) => {
    setStepLoading((prev) => ({ ...prev, [key]: loading }))
  }

  const normalizeRunStatus = (value) => String(value || '').toLowerCase()

  const normalizeStepStatus = (value) => {
    const normalized = String(value || '').toLowerCase()
    if (!normalized || normalized === 'idle') return 'idle'
    if (normalized === 'queued') return 'running'
    if (normalized === 'skipped') return 'success'
    return normalized
  }

  const statusFromState = (key) => {
    if (stepLoading[key]) return 'running'
    if (stepErrors[key]) return 'failed'
    if (stepResults[key]) return 'success'

    const runStepStatus = normalizeStepStatus(run?.step_statuses?.[key]?.status)
    if (runStepStatus !== 'idle') return runStepStatus

    if (!run) return 'idle'
    if (normalizeRunStatus(run.status) === 'running') return 'running'
    if (normalizeRunStatus(run.status) === 'failed') return 'failed'

    if (key === 'model') return run.schema_apply_result ? 'success' : 'idle'
    if (key === 'collect') return run.ingest_result ? 'success' : 'idle'
    if (key === 'process') return run.bridge_status || run.bridge_run ? 'success' : 'idle'
    if (key === 'extract') return run.bridge_run ? 'success' : 'idle'
    if (key === 'execute') return run.builder_submit_result ? 'success' : 'idle'
    if (key === 'apply') return run.headlines_snapshot ? 'success' : 'idle'
    return 'idle'
  }

  const steps = useMemo(
    () => STEP_DEFS.map((item) => ({ ...item, status: statusFromState(item.key) })),
    [run, stepLoading, stepErrors, stepResults],
  )

  const availableRuns = useMemo(() => {
    const merged = new Map()
    ;[run, ...(history || [])].filter(Boolean).forEach((item) => {
      if (item?.run_id && !merged.has(item.run_id)) merged.set(item.run_id, item)
    })
    return Array.from(merged.values()).sort((a, b) => String(b?.started_at || '').localeCompare(String(a?.started_at || '')))
  }, [run, history])

  const currentStepDetail = detailRunId ? detailCache?.[detailRunId]?.[detailStepKey] || null : null

  const panelResults = useMemo(() => ({
    model: stepResults.model || (
      run?.schema_commit_result || run?.schema_apply_result
        ? {
            schema_source: run?.schema_source,
            compiled_schema_script: run?.compiled_schema_script,
            kag_schema_export: run?.kag_schema_export,
            schema_commit_result: run?.schema_commit_result || run?.schema_apply_result,
            activate_result: run?.activate_result || run?.active_model_profile,
            active_model_profile: run?.active_model_profile,
          }
        : null
    ),
    collect: stepResults.collect || run?.ingest_result || null,
    process: stepResults.process || ((run?.process_preview || run?.bridge_status) ? { preview: run?.process_preview || null, status: run?.bridge_status || null } : null),
    extract: stepResults.extract || (run?.bridge_run ? { ...run?.bridge_run, runtime_profile: run?.runtime_profile } : null),
    execute: stepResults.execute || (
      run?.builder_submit_result
        ? { runtime_profile: run?.runtime_profile, builder_submit_result: run.builder_submit_result, bridge_last_run: run?.bridge_run || null, runtime_binding: run?.runtime_binding || null }
        : null
    ),
    apply: stepResults.apply || run?.headlines_snapshot || null,
  }), [run, stepResults])

  const loadHistory = async (projectId = params.project_id, options = {}) => {
    const { silent = false, preserve = true } = options
    setLoadingHistory(true)
    try {
      const data = await workflowApi.getHistory(projectId, 20)
      setHistory(Array.isArray(data?.runs) ? data.runs : [])
    } catch (error) {
      if (!silent) message.error(`读取历史失败: ${error.message}`)
      if (!preserve) setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  const loadLatest = async (projectId = params.project_id, options = {}) => {
    const { preserve = true } = options
    try {
      const data = await workflowApi.getLatestRun(projectId)
      setRun(data || null)
    } catch (error) {
      if (!preserve) setRun(null)
    }
  }

  const loadCurrentSchema = async (projectId = params.project_id) => {
    try {
      const data = await modelStudioApi.getCurrentSchema(projectId)
      const script = String(data?.schema_script || '').trim()
      if (script) setSchemaScript(script)
    } catch (error) {
      // 不阻断页面；当前 Schema 预览可在首次执行建模后获得。
    }
  }

  const runCollectStep = async () => {
    setLoading('collect', true)
    try {
      const result = await workflowApi.collectStep({
        max_entries_per_feed: params.max_entries_per_feed,
        hours_ago: params.hours_ago,
      })
      setStepResult('collect', result)
      message.success(`采集完成，新增 ${result?.inserted_count || 0} 条`)
    } catch (error) {
      setStepError('collect', error.message)
      message.error(`采集失败: ${error.message}`)
    } finally {
      setLoading('collect', false)
    }
  }

  const runProcessStep = async () => {
    setLoading('process', true)
    try {
      const result = await workflowApi.processStep({
        limit: params.bridge_limit,
        sample_lines: 5,
        allow_demo_fallback: false,
      })
      setStepResult('process', result)
      message.success('处理预览已更新')
    } catch (error) {
      setStepError('process', error.message)
      message.error(`处理失败: ${error.message}`)
    } finally {
      setLoading('process', false)
    }
  }

  const runModelStep = async () => {
    setLoading('model', true)
    try {
      const result = await workflowApi.modelStep({
        project_id: params.project_id,
        activate_label: 'workflow-step',
      })
      setStepResult('model', result)
      if (result?.compiled_schema_script) setSchemaScript(result.compiled_schema_script)
      message.success('建模阶段完成：OpenKS Schema 已提交并激活')
    } catch (error) {
      setStepError('model', error.message)
      message.error(`建模失败: ${error.message}`)
    } finally {
      setLoading('model', false)
    }
  }

  const runExecuteStep = async () => {
    setLoading('execute', true)
    try {
      const result = await workflowApi.executeStep({
        project_id: params.project_id,
        runtime_profile: params.runtime_profile,
        builder_command: params.builder_command || undefined,
        limit: params.bridge_limit,
        worker_num: params.worker_num,
      })
      setStepResult('execute', result)
      message.success(`执行完成，Builder job: ${result?.builder_submit_result?.job_id || '-'}`)
    } catch (error) {
      setStepError('execute', error.message)
      message.error(`执行失败: ${error.message}`)
    } finally {
      setLoading('execute', false)
    }
  }

  const runExtractStep = async () => {
    setLoading('extract', true)
    try {
      const result = await workflowApi.extractStep({
        project_id: params.project_id,
        limit: params.bridge_limit,
        force_full: params.force_full,
        use_active_model: true,
        worker_num: params.worker_num,
        runtime_profile: params.runtime_profile,
      })
      setStepResult('extract', result)
      message.success(`抽取完成，导出 ${result?.export_count || 0} 条`)
    } catch (error) {
      setStepError('extract', error.message)
      message.error(`抽取失败: ${error.message}`)
    } finally {
      setLoading('extract', false)
    }
  }

  const runApplyStep = async () => {
    setLoading('apply', true)
    try {
      const result = await workflowApi.applyStep({
        hours: params.hours_ago,
        top_n: params.headlines_top_n,
        allow_demo_fallback: false,
      })
      setStepResult('apply', result)
      message.success(`应用快照更新，返回 ${(result?.headlines || []).length} 条头条`)
    } catch (error) {
      setStepError('apply', error.message)
      message.error(`应用阶段失败: ${error.message}`)
    } finally {
      setLoading('apply', false)
    }
  }

  const runWorkflow = async () => {
    setRunning(true)
    try {
      const payload = {
        ...params,
        builder_command: params.builder_command || undefined,
      }
      const result = await workflowApi.runNewsWorkflow(payload)
      setRun(result || null)
      setStepResults({})
      setStepErrors(initialErrors)
      setSubmittedRunId(result?.run_id || '')
      await loadHistory(params.project_id, { silent: true, preserve: true })
      message.info(`流程已提交: ${result?.run_id || '-'}`)
    } catch (error) {
      message.error(`流程执行失败: ${error.message}`)
    } finally {
      setRunning(false)
    }
  }

  const replayRun = async (runId) => {
    try {
      const data = await workflowApi.getRun(runId)
      setRun(data || null)
      setDetailRunId(runId)
      setDetailStepKey('apply')
      setDetailDrawerOpen(true)
    } catch (error) {
      message.error(`回放失败: ${error.message}`)
    }
  }

  const openStepDetail = (stepKey, targetRunId) => {
    const runId = targetRunId || run?.run_id || history?.[0]?.run_id
    if (!runId) {
      message.info('暂无可回放的运行记录')
      return
    }
    setDetailRunId(runId)
    setDetailStepKey(stepKey)
    setDetailDrawerOpen(true)
  }

  const loadStepDetail = async (runId, stepKey, force = false) => {
    if (!runId || !stepKey) return
    if (!force && detailCache?.[runId]?.[stepKey]) return
    setDetailLoading(true)
    try {
      const data = await workflowApi.getRunStepDetail(runId, stepKey)
      setDetailCache((prev) => ({
        ...prev,
        [runId]: {
          ...(prev?.[runId] || {}),
          [stepKey]: data,
        },
      }))
    } catch (error) {
      message.error(`读取阶段详情失败: ${error.message}`)
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    loadLatest(defaultParams.project_id, { preserve: false })
    loadHistory(defaultParams.project_id, { silent: true, preserve: false })
    loadCurrentSchema(defaultParams.project_id)
  }, [])

  useEffect(() => {
    const runId = run?.run_id
    const projectId = run?.project_id || params.project_id
    const status = normalizeRunStatus(run?.status)
    if (!runId || !ACTIVE_RUN_STATUSES.has(status)) return undefined

    let cancelled = false
    const tick = async () => {
      try {
        const [runData, historyData] = await Promise.all([
          workflowApi.getRun(runId),
          workflowApi.getHistory(projectId, 20),
        ])
        if (cancelled) return
        if (runData) setRun(runData)
        if (Array.isArray(historyData?.runs)) setHistory(historyData.runs)
      } catch (error) {
        if (cancelled) return
      }
    }

    tick()
    const timer = window.setInterval(tick, 3000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [run?.run_id, run?.status, run?.project_id, params.project_id])

  useEffect(() => {
    const status = normalizeRunStatus(run?.status)
    if (!run?.run_id || run.run_id !== submittedRunId || !TERMINAL_RUN_STATUSES.has(status)) return

    if (status === 'success') {
      message.success(`流程执行完成: ${run.run_id}`)
    } else if (status === 'partial_success') {
      message.warning(`流程部分完成: ${run.run_id}`)
    } else {
      message.error(`流程执行失败: ${run?.error || run?.status_reason || run.run_id}`)
    }
    setSubmittedRunId('')
  }, [run, submittedRunId])

  useEffect(() => {
    if (!detailDrawerOpen || !detailRunId || !detailStepKey) return
    loadStepDetail(detailRunId, detailStepKey)
  }, [detailDrawerOpen, detailRunId, detailStepKey])

  useEffect(() => {
    const targetRunId = String(searchParams.get('run_id') || '').trim()
    const targetStep = String(searchParams.get('step') || '').trim()
    const openDetail = String(searchParams.get('open_detail') || '').trim()
    if (!targetRunId || !targetStep || openDetail !== '1') return
    setDetailRunId(targetRunId)
    setDetailStepKey(targetStep)
    setDetailDrawerOpen(true)
  }, [searchParams])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <WorkflowHeader
        runId={run?.run_id}
        status={run?.status}
        runtimeProfile={run?.runtime_profile || params.runtime_profile}
      />

      <GlobalRunControlBar
        params={params}
        running={running}
        onChange={setParam}
        onRun={runWorkflow}
      />

      <Alert
        type="info"
        showIcon
        message="主链工作方式"
        description="支持单步执行与一键全流程。当前页面固定走 kag_openspg 主链；工作流提交后会异步执行并自动轮询状态，点击阶段卡片可查看该阶段的真实输入、输出与可视化结果。"
      />

      {normalizeRunStatus(run?.status) === 'partial_success' ? (
        <Alert
          type="warning"
          showIcon
          message="本次流程为部分成功"
          description={(run?.warnings || []).join('；') || run?.status_reason || '部分阶段已完成，但 Schema/Builder 未完全成功。'}
        />
      ) : null}

      {normalizeRunStatus(run?.status) === 'failed' ? (
        <Alert
          type="error"
          showIcon
          message="本次流程失败"
          description={run?.error || run?.status_reason || '请查看运行摘要与阶段产物详情。'}
        />
      ) : null}

      <PipelineStepper
        steps={steps}
        activeKey={detailDrawerOpen ? detailStepKey : undefined}
        onStepClick={(stepKey) => openStepDetail(stepKey)}
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12}>
          <StepModelPanel
            loading={stepLoading.model}
            result={panelResults.model}
            error={stepErrors.model}
            schemaScript={schemaScript}
            onRun={runModelStep}
          />
        </Col>
        <Col xs={24} xl={12}>
          <StepCollectPanel
            loading={stepLoading.collect}
            result={panelResults.collect}
            error={stepErrors.collect}
            onRun={runCollectStep}
          />
        </Col>
        <Col xs={24} xl={12}>
          <StepProcessPanel
            loading={stepLoading.process}
            result={panelResults.process}
            error={stepErrors.process}
            onRun={runProcessStep}
          />
        </Col>
        <Col xs={24} xl={12}>
          <StepExtractPanel
            loading={stepLoading.extract}
            result={panelResults.extract}
            error={stepErrors.extract}
            onRun={runExtractStep}
          />
        </Col>
        <Col xs={24} xl={12}>
          <StepExecutePanel
            loading={stepLoading.execute}
            result={panelResults.execute}
            error={stepErrors.execute}
            onRun={runExecuteStep}
          />
        </Col>
        <Col xs={24}>
          <StepApplyPanel
            loading={stepLoading.apply}
            result={panelResults.apply}
            error={stepErrors.apply}
            onRun={runApplyStep}
          />
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <UnorderedListOutlined />
            运行历史
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => loadHistory(params.project_id)} loading={loadingHistory}>
            刷新
          </Button>
        }
      >
        <RunHistoryTable runs={history} loading={loadingHistory} onReplay={replayRun} />
      </Card>

      <Card title="当前运行摘要" extra={<Button onClick={() => openStepDetail(detailStepKey || 'apply', run?.run_id)} disabled={!run}>查看阶段详情</Button>}>
        <pre
          style={{
            margin: 0,
            maxHeight: 220,
            overflow: 'auto',
            background: '#f6f9fc',
            border: '1px solid #dbe5ef',
            borderRadius: 8,
            padding: 12,
            fontSize: 12,
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {JSON.stringify(
            {
              run_id: run?.run_id,
              runtime_profile: run?.runtime_profile || params.runtime_profile,
              status: run?.status,
              schema_source: run?.schema_source,
              compiled_schema_script: run?.compiled_schema_script,
              kag_schema_export: run?.kag_schema_export,
              schema_commit_result: run?.schema_commit_result,
              ingest_result: run?.ingest_result,
              bridge_run: run?.bridge_run,
              schema_apply_result: run?.schema_apply_result,
              activate_result: run?.activate_result,
              builder_submit_result: run?.builder_submit_result,
              runtime_binding: run?.runtime_binding,
              headlines_snapshot: run?.headlines_snapshot,
              step_statuses: run?.step_statuses,
              warnings: run?.warnings,
              status_reason: run?.status_reason,
            },
            null,
            2,
          )}
        </pre>
      </Card>

      <StepDetailDrawer
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
        runs={availableRuns}
        selectedRunId={detailRunId}
        selectedStepKey={detailStepKey}
        onRunChange={(runId) => setDetailRunId(runId)}
        onStepChange={(stepKey) => setDetailStepKey(stepKey)}
        onRefresh={() => loadStepDetail(detailRunId, detailStepKey, true)}
        detail={currentStepDetail}
        loading={detailLoading}
      />
    </div>
  )
}

export default WorkflowWorkbenchPage
