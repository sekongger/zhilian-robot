import React, { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Button,
  Card,
  Col,
  Empty,
  Input,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  message
} from 'antd'
import { ApiOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import openApiService from '../services/openApiService'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const ApplicationCenterPage = () => {
  const [searchParams] = useSearchParams()
  const [headlines, setHeadlines] = useState([])
  const [headlinesLoading, setHeadlinesLoading] = useState(false)
  const [querying, setQuerying] = useState(false)
  const [question, setQuestion] = useState('本周机器人产业链最重要三件事是什么？')
  const [queryResult, setQueryResult] = useState(null)
  const [traceResult, setTraceResult] = useState(null)

  const incomingQuestion = String(searchParams.get('question') || '').trim()
  const incomingTraceId = String(searchParams.get('trace_id') || '').trim()
  const incomingStatementId = String(searchParams.get('statement_id') || '').trim()
  const incomingDocId = String(searchParams.get('doc_id') || '').trim()
  const incomingAutoQuery = String(searchParams.get('auto_query') || '').trim()

  const loadHeadlines = async () => {
    setHeadlinesLoading(true)
    try {
      const data = await openApiService.getHeadlines({ hours: 24, top_n: 10 })
      setHeadlines(Array.isArray(data?.headlines) ? data.headlines : [])
    } catch (error) {
      message.error(`读取头条失败: ${error.message}`)
      setHeadlines([])
    } finally {
      setHeadlinesLoading(false)
    }
  }

  useEffect(() => {
    loadHeadlines()
  }, [])

  const queryKnowledgeByText = async (rawText) => {
    const text = String(rawText || '').trim()
    if (!text) {
      message.warning('请输入问题')
      return
    }
    setQuerying(true)
    try {
      const data = await openApiService.queryKnowledge({
        query: text,
        query_type: 'semantic',
        top_k: 10,
        filters: { hours: 24 },
        include_evidence: true
      })
      setQueryResult(data || null)
      setTraceResult(null)
    } catch (error) {
      message.error(`查询失败: ${error.message}`)
      setQueryResult(null)
    } finally {
      setQuerying(false)
    }
  }

  const queryKnowledge = async () => queryKnowledgeByText(question)

  const loadTraceById = async (traceId) => {
    const id = String(traceId || '').trim()
    if (!id) return
    try {
      const trace = await openApiService.getTrace(id)
      setTraceResult(trace || null)
    } catch (error) {
      message.error(`读取 Trace 失败: ${error.message}`)
      setTraceResult(null)
    }
  }

  const loadTrace = async () => {
    if (!queryResult?.trace_id) return
    await loadTraceById(queryResult.trace_id)
  }

  const headlineColumns = useMemo(() => [
    {
      title: '事件标题',
      dataIndex: 'headline_title',
      key: 'headline_title',
      ellipsis: true,
    },
    {
      title: '企业',
      dataIndex: 'companies',
      key: 'companies',
      render: (companies = []) => (
        <Space wrap>
          {(companies || []).slice(0, 3).map((name) => (
            <Tag key={name}>{name}</Tag>
          ))}
        </Space>
      )
    },
    {
      title: '热度',
      dataIndex: 'headline_score',
      key: 'headline_score',
      width: 90,
    },
    {
      title: '来源数',
      dataIndex: 'source_count',
      key: 'source_count',
      width: 90,
    }
  ], [])

  useEffect(() => {
    if (incomingQuestion) {
      setQuestion(incomingQuestion)
      if (incomingAutoQuery === '1') {
        queryKnowledgeByText(incomingQuestion)
      }
    }
    if (incomingTraceId) {
      loadTraceById(incomingTraceId)
    }
  }, [incomingQuestion, incomingTraceId, incomingAutoQuery])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space direction="vertical" size={4}>
          <Space>
            <ApiOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
            <Title level={3} style={{ margin: 0 }}>应用中心</Title>
            <Tag color="blue">Open API</Tag>
          </Space>
          <Text type="secondary">
            平台能力对外以 `/api/v1/open/*` 暴露，适用于生产智能体接入；本页用于能力校验与联调。
          </Text>
          {incomingTraceId || incomingStatementId || incomingDocId ? (
            <Space wrap>
              {incomingTraceId ? <Tag color="blue">trace: {incomingTraceId}</Tag> : null}
              {incomingStatementId ? <Tag color="cyan">statement: {incomingStatementId}</Tag> : null}
              {incomingDocId ? <Tag color="gold">doc: {incomingDocId}</Tag> : null}
            </Space>
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card
            title="产业头条能力"
            extra={<Button icon={<ReloadOutlined />} onClick={loadHeadlines} loading={headlinesLoading}>刷新</Button>}
          >
            <Table
              rowKey={(row) => row.event_id}
              loading={headlinesLoading}
              dataSource={headlines}
              columns={headlineColumns}
              pagination={false}
              locale={{ emptyText: <Empty description="暂无头条" /> }}
            />
          </Card>
        </Col>

        <Col xs={24} xl={12}>
          <Card
            title="知识查询能力"
            extra={<Button type="primary" icon={<SearchOutlined />} onClick={queryKnowledge} loading={querying}>查询</Button>}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <TextArea
                value={question}
                rows={4}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="输入产业动态问题"
              />

              {queryResult ? (
                <>
                  <Paragraph style={{ marginBottom: 0 }}>
                    <Text strong>回答：</Text>
                    <br />
                    <Text>{queryResult.answer || '暂无回答'}</Text>
                  </Paragraph>

                  <Space wrap>
                    <Tag color="processing">trace_id: {queryResult.trace_id}</Tag>
                    <Tag color="success">事实: {(queryResult.knowledge_objects || []).length}</Tag>
                    <Tag color="gold">证据: {(queryResult.evidences || []).length}</Tag>
                    <Button size="small" onClick={loadTrace}>查看 Trace</Button>
                  </Space>

                  {traceResult ? (
                    <pre style={{
                      margin: 0,
                      maxHeight: 220,
                      overflow: 'auto',
                      background: '#f6f9fc',
                      border: '1px solid #dbe5ef',
                      borderRadius: 8,
                      padding: 10,
                      fontSize: 12,
                      lineHeight: 1.45,
                      whiteSpace: 'pre-wrap'
                    }}>
                      {JSON.stringify(traceResult, null, 2)}
                    </pre>
                  ) : null}
                </>
              ) : (
                <Empty description="输入问题后可查看 Open API 返回" />
              )}
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ApplicationCenterPage
