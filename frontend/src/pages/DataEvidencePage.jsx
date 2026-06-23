import React, { useMemo, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import { DatabaseOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import DocumentPipelinePage from './DocumentPipelinePage'
import resourceApi from '../services/resourceApi'

const { Title, Text } = Typography

const DataEvidencePage = () => {
  const [traceId, setTraceId] = useState('')
  const [statementId, setStatementId] = useState('')
  const [docId, setDocId] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sortBy, setSortBy] = useState('publish_time')
  const [sortOrder, setSortOrder] = useState('desc')
  const navigate = useNavigate()

  const sortByOptions = [
    { value: 'publish_time', label: '发布时间' },
    { value: 'source_name', label: '来源名称' },
    { value: 'source_collection', label: '来源集合' },
    { value: 'statement_id', label: 'statement_id' },
    { value: 'doc_id', label: 'doc_id' },
  ]

  const jumpToApplication = (row) => {
    const params = new URLSearchParams()
    const question = String(row?.title || row?.snippet || '').trim()
    const trace = String(result?.query?.trace_id || row?.trace_id || '').trim()
    const statement = String(row?.statement_id || '').trim()
    const doc = String(row?.doc_id || '').trim()
    if (question) params.set('question', question)
    if (trace) params.set('trace_id', trace)
    if (statement) params.set('statement_id', statement)
    if (doc) params.set('doc_id', doc)
    params.set('auto_query', '1')
    navigate(`/applications?${params.toString()}`)
  }

  const jumpToIndustryQa = (row) => {
    const params = new URLSearchParams()
    const question = String(row?.title || row?.snippet || '').trim()
    const trace = String(result?.query?.trace_id || row?.trace_id || '').trim()
    const statement = String(row?.statement_id || '').trim()
    const doc = String(row?.doc_id || '').trim()
    if (question) params.set('question', question)
    if (trace) params.set('trace_id', trace)
    if (statement) params.set('statement_id', statement)
    if (doc) params.set('doc_id', doc)
    navigate(`/agent/industry-qa?${params.toString()}`)
  }

  const evidenceColumns = useMemo(
    () => [
      {
        title: 'statement_id',
        dataIndex: 'statement_id',
        key: 'statement_id',
        width: 180,
        render: (value) => value || '-',
      },
      {
        title: 'doc_id',
        dataIndex: 'doc_id',
        key: 'doc_id',
        width: 180,
        render: (value) => value || '-',
      },
      {
        title: '证据',
        dataIndex: 'title',
        key: 'title',
        ellipsis: true,
        render: (_, row) => (
          <Space direction="vertical" size={2}>
            <Text strong>{row.title || '-'}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{row.snippet || ''}</Text>
          </Space>
        ),
      },
      {
        title: '来源',
        dataIndex: 'source_name',
        key: 'source_name',
        width: 220,
        render: (_, row) => (
          <Space direction="vertical" size={2}>
            <Text>{row.source_name || '-'}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{row.source_url || ''}</Text>
          </Space>
        ),
      },
      {
        title: '来源集合',
        dataIndex: 'source_collection',
        key: 'source_collection',
        width: 140,
        render: (value) => <Tag color="blue">{value || '-'}</Tag>,
      },
      {
        title: '联动',
        key: 'actions',
        width: 220,
        fixed: 'right',
        render: (_, row) => (
          <Space size={4}>
            <Button size="small" onClick={() => jumpToApplication(row)}>去应用中心</Button>
            <Button size="small" type="primary" ghost onClick={() => jumpToIndustryQa(row)}>去产业问答</Button>
          </Space>
        ),
      },
    ],
    [jumpToApplication, jumpToIndustryQa],
  )

  const documentColumns = useMemo(
    () => [
      {
        title: 'doc_id',
        dataIndex: 'doc_id',
        key: 'doc_id',
        width: 180,
      },
      {
        title: '标题',
        dataIndex: 'title',
        key: 'title',
        ellipsis: true,
      },
      {
        title: '来源',
        dataIndex: 'source_name',
        key: 'source_name',
        width: 180,
      },
      {
        title: '来源集合',
        dataIndex: 'source_collection',
        key: 'source_collection',
        width: 140,
        render: (value) => <Tag color="cyan">{value || '-'}</Tag>,
      },
    ],
    [],
  )

  const doLookup = async (options = {}) => {
    const nextPage = options.page || page
    const nextPageSize = options.pageSize || pageSize
    const nextSortBy = options.sortBy || sortBy
    const nextSortOrder = options.sortOrder || sortOrder

    const payload = {
      trace_id: String(traceId || '').trim() || undefined,
      statement_id: String(statementId || '').trim() || undefined,
      doc_id: String(docId || '').trim() || undefined,
      hours: 24,
      limit: 200,
      page: nextPage,
      page_size: nextPageSize,
      sort_by: nextSortBy,
      sort_order: nextSortOrder,
    }
    if (!payload.trace_id && !payload.statement_id && !payload.doc_id) {
      message.warning('请至少输入 trace_id / statement_id / doc_id 之一')
      return
    }

    setLoading(true)
    try {
      const data = await resourceApi.lookupEvidence(payload)
      setResult(data || null)
      setPage(nextPage)
      setPageSize(nextPageSize)
      setSortBy(nextSortBy)
      setSortOrder(nextSortOrder)
      message.success(`联查完成：命中 ${data?.total || 0} 条证据`)
    } catch (error) {
      setResult(null)
      message.error(`联查失败: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const tabItems = [
    {
      key: 'lookup',
      label: '证据联查',
      children: (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Card title="证据联查说明">
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Text>
                证据联查用于按 <Text code>trace_id</Text>、<Text code>statement_id</Text> 或 <Text code>doc_id</Text> 回溯一条结论背后的原始文档、陈述和来源。
              </Text>
              <Row gutter={[12, 12]}>
                <Col xs={24} md={8}>
                  <Card size="small" bordered={false} className="platform-inner-soft-card">
                    <Space direction="vertical" size={6}>
                      <Text strong>从问答或应用回溯</Text>
                      <Text type="secondary">先在应用中心或产业问答里拿到 trace_id，再回到这里查看完整证据链。</Text>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card size="small" bordered={false} className="platform-inner-soft-card">
                    <Space direction="vertical" size={6}>
                      <Text strong>从 statement_id 查</Text>
                      <Text type="secondary">适合追某一条知识陈述来自哪几篇资讯或研报。</Text>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card size="small" bordered={false} className="platform-inner-soft-card">
                    <Space direction="vertical" size={6}>
                      <Text strong>从 doc_id 查</Text>
                      <Text type="secondary">适合查看某篇文档被抽成了哪些实体、陈述和上下文。</Text>
                    </Space>
                  </Card>
                </Col>
              </Row>
              <Space wrap>
                <Button onClick={() => navigate('/applications')}>去应用中心获取 trace_id</Button>
                <Button type="primary" ghost onClick={() => navigate('/agent/industry-qa')}>去产业问答获取 trace_id</Button>
              </Space>
            </Space>
          </Card>
          <Card title="联查入口">
            <Row gutter={[12, 12]}>
              <Col xs={24} md={8}>
                <Input
                  value={traceId}
                  onChange={(e) => setTraceId(e.target.value)}
                  placeholder="trace_id"
                  allowClear
                />
              </Col>
              <Col xs={24} md={8}>
                <Input
                  value={statementId}
                  onChange={(e) => setStatementId(e.target.value)}
                  placeholder="statement_id"
                  allowClear
                />
              </Col>
              <Col xs={24} md={8}>
                <Input
                  value={docId}
                  onChange={(e) => setDocId(e.target.value)}
                  placeholder="doc_id"
                  allowClear
                />
              </Col>
              <Col xs={24} md={6}>
                <Select
                  value={sortBy}
                  options={sortByOptions}
                  onChange={(value) => setSortBy(value)}
                  style={{ width: '100%' }}
                />
              </Col>
              <Col xs={24} md={6}>
                <Select
                  value={sortOrder}
                  options={[
                    { value: 'desc', label: '倒序' },
                    { value: 'asc', label: '正序' },
                  ]}
                  onChange={(value) => setSortOrder(value)}
                  style={{ width: '100%' }}
                />
              </Col>
              <Col span={24}>
                <Button
                  type="primary"
                  onClick={() => doLookup({ page: 1 })}
                  loading={loading}
                >
                  开始联查
                </Button>
              </Col>
            </Row>
          </Card>

          <Card title="证据结果">
            {result ? (
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                <Space wrap>
                  <Tag color="processing">命中: {result.total || 0}</Tag>
                  {result.query?.trace_id ? <Tag color="blue">trace: {result.query.trace_id}</Tag> : null}
                  {result.query?.statement_id ? <Tag color="cyan">statement: {result.query.statement_id}</Tag> : null}
                  {result.query?.doc_id ? <Tag color="gold">doc: {result.query.doc_id}</Tag> : null}
                </Space>
                <Table
                  rowKey={(row, index) => `${row.statement_id || '-'}::${row.doc_id || '-'}::${index}`}
                  dataSource={result.items || []}
                  columns={evidenceColumns}
                  pagination={{
                    current: result?.pagination?.page || page,
                    pageSize: result?.pagination?.page_size || pageSize,
                    total: result?.total || 0,
                    showSizeChanger: true,
                    pageSizeOptions: [10, 20, 50, 100],
                  }}
                  onChange={(pagination) => {
                    doLookup({
                      page: pagination.current,
                      pageSize: pagination.pageSize,
                    })
                  }}
                  scroll={{ x: 1280 }}
                  locale={{ emptyText: <Empty description="无证据结果" /> }}
                />
              </Space>
            ) : (
              <Empty description="请输入任一标识后联查" />
            )}
          </Card>

          <Card title="文档快照与 Trace">
            <Row gutter={[12, 12]}>
              <Col xs={24} xl={14}>
                <Table
                  rowKey={(row, index) => `${row.source_collection || '-'}::${row.doc_id || '-'}::${index}`}
                  dataSource={result?.documents || []}
                  columns={documentColumns}
                  pagination={{ pageSize: 6 }}
                  locale={{ emptyText: <Empty description="无文档快照" /> }}
                />
              </Col>
              <Col xs={24} xl={10}>
                {result?.trace ? (
                  <pre
                    style={{
                      margin: 0,
                      minHeight: 260,
                      maxHeight: 340,
                      overflow: 'auto',
                      background: '#f6f9fc',
                      border: '1px solid #dbe5ef',
                      borderRadius: 8,
                      padding: 10,
                      fontSize: 12,
                      lineHeight: 1.45,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {JSON.stringify(result.trace, null, 2)}
                  </pre>
                ) : (
                  <Empty description="无 trace 数据" />
                )}
              </Col>
            </Row>
          </Card>

          <Card title="结构化语义对象">
            <Row gutter={[12, 12]}>
              <Col xs={24} xl={12}>
                {result?.statement ? (
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    <Tag color="blue">statement_id: {result.statement.statement_id || '-'}</Tag>
                    <Text><Text strong>subject_id:</Text> {result.statement.subject_id || '-'}</Text>
                    <Text><Text strong>predicate_id:</Text> {result.statement.predicate_id || '-'}</Text>
                    <Text><Text strong>object_id:</Text> {result.statement.object_id || '-'}</Text>
                    <Text><Text strong>confidence:</Text> {result.statement.confidence ?? '-'}</Text>
                    <Text><Text strong>doc_id:</Text> {result.statement.doc_id || '-'}</Text>
                    <Text><Text strong>context_scenario:</Text> {result.statement.context_scenario || '-'}</Text>
                  </Space>
                ) : (
                  <Empty description="无 statement 结构数据" />
                )}
              </Col>
              <Col xs={24} xl={12}>
                <Table
                  rowKey={(row, index) => `${row.context_id || '-'}::${index}`}
                  dataSource={result?.contexts || []}
                  pagination={false}
                  locale={{ emptyText: <Empty description="无 context 结构数据" /> }}
                  columns={[
                    { title: 'context_id', dataIndex: 'context_id', key: 'context_id' },
                    { title: 'type', dataIndex: 'context_type', key: 'context_type' },
                    { title: 'doc_id', dataIndex: 'doc_id', key: 'doc_id' },
                    { title: 'begin_time', dataIndex: 'begin_time', key: 'begin_time' },
                    { title: 'end_time', dataIndex: 'end_time', key: 'end_time' },
                  ]}
                  scroll={{ x: 880 }}
                  size="small"
                />
              </Col>
            </Row>
          </Card>
        </Space>
      ),
    },
    {
      key: 'pipeline',
      label: '文档处理中心',
      children: <DocumentPipelinePage />,
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space direction="vertical" size={6}>
          <Space>
            <DatabaseOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
            <Title level={3} style={{ margin: 0 }}>数据与证据</Title>
            <Tag color="cyan">Traceable Evidence</Tag>
          </Space>
          <Text type="secondary">
            按文档、事实与来源进行证据回溯，支持从 trace_id/statement_id/doc_id 快速定位。
          </Text>
        </Space>
      </Card>
      <Tabs items={tabItems} />
    </div>
  )
}

export default DataEvidencePage
