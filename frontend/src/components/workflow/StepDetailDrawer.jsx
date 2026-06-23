import React from 'react'
import {
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import StepVisualizationPanel from './StepVisualizationPanel'

const { Text, Title } = Typography

const STEP_LABELS = {
  model: '1. 建模',
  collect: '2. 采集',
  process: '3. 处理',
  extract: '4. 抽取',
  execute: '5. 执行',
  apply: '6. 应用',
}

const STATUS_COLOR = {
  queued: 'default',
  running: 'processing',
  success: 'success',
  partial_success: 'warning',
  failed: 'error',
}

const formatTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const CodeBlock = ({ content }) => (
  <pre
    style={{
      margin: 0,
      maxHeight: 300,
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
    {content}
  </pre>
)

const JsonBlock = ({ payload }) => <CodeBlock content={JSON.stringify(payload, null, 2)} />

const MetricsGrid = ({ metrics = [] }) => {
  if (!metrics.length) return null
  return (
    <Row gutter={[12, 12]}>
      {metrics.map((item) => (
        <Col xs={12} md={8} key={item.label}>
          <Card size="small">
            <Text type="secondary">{item.label}</Text>
            <div style={{ fontSize: 18, fontWeight: 600, marginTop: 6 }}>{String(item.value ?? '-')}</div>
          </Card>
        </Col>
      ))}
    </Row>
  )
}

const DataSections = ({ section }) => {
  if (!section) return <Empty description="暂无数据" />
  const tables = []
  if (section.table) tables.push(section.table)
  for (const item of section.sections || []) {
    if (item?.type === 'table' && item.table) tables.push(item.table)
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <MetricsGrid metrics={section.metrics || []} />

      {section.code ? (
        <Card size="small" title={section.code.title || '代码'}>
          <CodeBlock content={section.code.content || ''} />
        </Card>
      ) : null}

      {section.json ? (
        <Card size="small" title={section.json.title || 'JSON'}>
          <JsonBlock payload={section.json.payload} />
        </Card>
      ) : null}

      {tables.map((table) => (
        <Card size="small" title={table.title} key={table.title}>
          <Table
            rowKey={(row, idx) => row.id || row.doc_id || row.event_id || row.type_name || idx}
            size="small"
            pagination={false}
            scroll={{ x: 720 }}
            dataSource={table.rows || []}
            columns={table.columns || []}
          />
        </Card>
      ))}

      {(section.sections || [])
        .filter((item) => item?.type === 'code' || item?.type === 'json')
        .map((item) => (
          <Card size="small" title={item.title} key={item.title}>
            {item.type === 'code' ? <CodeBlock content={item.content || ''} /> : <JsonBlock payload={item.payload} />}
          </Card>
        ))}
    </Space>
  )
}

const StepDetailDrawer = ({
  open,
  onClose,
  runs,
  selectedRunId,
  selectedStepKey,
  onRunChange,
  onStepChange,
  onRefresh,
  detail,
  loading,
}) => {
  const currentRun = (runs || []).find((item) => item.run_id === selectedRunId) || null
  const runOptions = (runs || []).map((item) => ({
    label: `${item.run_id} | ${item.status || '-'}`,
    value: item.run_id,
  }))

  return (
    <Drawer
      title="阶段详情"
      open={open}
      onClose={onClose}
      width={1180}
      destroyOnClose={false}
      extra={<Button icon={<ReloadOutlined />} onClick={onRefresh} loading={loading}>刷新</Button>}
    >
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card size="small">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space wrap>
                <Text type="secondary">运行记录</Text>
                <Select
                  style={{ minWidth: 420 }}
                  value={selectedRunId || undefined}
                  options={runOptions}
                  onChange={onRunChange}
                  placeholder="选择 run_id"
                />
              </Space>
              {currentRun?.status ? <Tag color={STATUS_COLOR[currentRun.status] || 'default'}>{currentRun.status}</Tag> : null}
            </Space>

            <Space wrap>
              <Tag color="processing">run_id: {currentRun?.run_id || '-'}</Tag>
              <Tag>开始: {formatTime(currentRun?.started_at)}</Tag>
              <Tag>结束: {formatTime(currentRun?.finished_at)}</Tag>
              {Array.isArray(currentRun?.warnings) && currentRun.warnings.length > 0 ? (
                <Tag color="warning">{currentRun.warnings[0]}</Tag>
              ) : null}
            </Space>
          </Space>
        </Card>

        <Row gutter={16}>
          <Col xs={24} lg={5}>
            <Card size="small" title="阶段导航">
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                {Object.entries(STEP_LABELS).map(([key, label]) => {
                  const active = key === selectedStepKey
                  const status = currentRun?.step_statuses?.[key]?.status
                  return (
                    <Button
                      key={key}
                      block
                      type={active ? 'primary' : 'default'}
                      onClick={() => onStepChange(key)}
                    >
                      {label}{status ? ` · ${status}` : ''}
                    </Button>
                  )
                })}
              </Space>
            </Card>
          </Col>

          <Col xs={24} lg={19}>
            <Card size="small">
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <div>
                  <Title level={4} style={{ margin: 0 }}>{detail?.meta?.title || STEP_LABELS[selectedStepKey] || '阶段详情'}</Title>
                  <Text type="secondary">{detail?.meta?.description || '查看本阶段的真实输入、输出与可视化结果。'}</Text>
                  {detail?.meta?.summary ? (
                    <div style={{ marginTop: 8, fontSize: 13, color: '#334155' }}>{detail.meta.summary}</div>
                  ) : null}
                </div>

                <Tabs
                  items={[
                    {
                      key: 'input',
                      label: '输入',
                      children: <DataSections section={detail?.input} />,
                    },
                    {
                      key: 'output',
                      label: '输出',
                      children: <DataSections section={detail?.output} />,
                    },
                    {
                      key: 'visualization',
                      label: '可视化',
                      children: <StepVisualizationPanel visualization={detail?.visualization} />,
                    },
                  ]}
                />
              </Space>
            </Card>
          </Col>
        </Row>
      </Space>
    </Drawer>
  )
}

export default StepDetailDrawer
