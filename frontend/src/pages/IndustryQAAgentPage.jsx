import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Collapse,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Empty,
  Input,
  List,
  Row,
  Segmented,
  Space,
  Table,
  Tag,
  Typography,
  message
} from 'antd'
import { DeleteOutlined, MessageOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons'
import industryQaApi from '../services/industryQaApi'
import openApiService from '../services/openApiService'
import { buildOpenSpgGraphModel, buildTraceOverview } from './industryQaTraceUtils.mjs'
import { buildAssistantPlaceholder } from './industryQaChatStatus.mjs'
import { parseReleaseContext } from './knowledgeContext.mjs'

const { Title, Text } = Typography
const { TextArea } = Input

const traceCardStyle = {
  border: '1px solid #dbe5ef',
  borderRadius: 12,
  padding: 14,
  background: 'linear-gradient(180deg, #ffffff 0%, #f7fbff 100%)',
  minHeight: 220,
}

const graphPalette = {
  anchor: { fill: '#e0f2fe', stroke: '#0b6e99' },
  document: { fill: '#eef6ff', stroke: '#4d7ea8' },
  statement: { fill: '#fff4de', stroke: '#d69e2e' },
  target: { fill: '#e7f7ef', stroke: '#2f855a' },
}

const OpenSpgGraphPreview = ({ model }) => {
  if (!model?.nodes?.length) {
    return <Empty description="当前 trace 暂无可视化图谱路径" />
  }

  const anchorNode = model.nodes.find((item) => item.type === 'anchor')
  const statementNodes = model.nodes.filter((item) => item.type === 'statement')
  const documentNodes = model.nodes.filter((item) => item.type === 'document')
  const targetNodes = model.nodes.filter((item) => item.type === 'target')

  const nodePositions = {}
  if (anchorNode) {
    nodePositions[anchorNode.id] = { x: 100, y: 160 }
  }
  statementNodes.forEach((item, index) => {
    nodePositions[item.id] = { x: 300, y: 90 + index * 90 }
  })
  documentNodes.forEach((item, index) => {
    nodePositions[item.id] = { x: 700, y: 90 + index * 90 }
  })
  targetNodes.forEach((item, index) => {
    nodePositions[item.id] = { x: 500, y: 90 + index * 90 }
  })

  const nodeStyle = (type) => graphPalette[type] || graphPalette.target

  return (
    <div style={{
      border: '1px solid #dbe5ef',
      borderRadius: 12,
      background: 'radial-gradient(circle at top left, #f8fdff 0%, #f3f7fb 48%, #eef2f6 100%)',
      overflow: 'hidden',
      padding: 12,
    }}>
      <svg viewBox="0 0 880 320" style={{ width: '100%', height: 320 }}>
        <defs>
          <marker id="qa-trace-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#8aa4b8" />
          </marker>
        </defs>

        {model.edges.map((edge, index) => {
          const from = nodePositions[edge.from]
          const to = nodePositions[edge.to]
          if (!from || !to) return null
          const midX = (from.x + to.x) / 2
          const midY = (from.y + to.y) / 2
          return (
            <g key={`${edge.from}-${edge.to}-${index}`}>
              <path
                d={`M ${from.x + 70} ${from.y} C ${midX - 40} ${from.y}, ${midX + 10} ${to.y}, ${to.x - 70} ${to.y}`}
                fill="none"
                stroke="#8aa4b8"
                strokeWidth="2"
                markerEnd="url(#qa-trace-arrow)"
              />
              <text x={midX} y={midY - 8} textAnchor="middle" style={{ fontSize: 12, fill: '#5b7183', fontWeight: 600 }}>
                {edge.label}
              </text>
            </g>
          )
        })}

        {model.nodes.map((node) => {
          const pos = nodePositions[node.id]
          if (!pos) return null
          const style = nodeStyle(node.type)
          return (
            <g key={node.id}>
              <rect
                x={pos.x - 72}
                y={pos.y - 28}
                width="144"
                height="56"
                rx="16"
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth="2"
              />
              <text x={pos.x} y={pos.y - 6} textAnchor="middle" style={{ fontSize: 12, fill: '#23364a', fontWeight: 700 }}>
                {node.type === 'anchor' ? '问题锚点' : node.type === 'document' ? '关联文档' : node.type === 'statement' ? '真实关系' : '图谱命中'}
              </text>
              <text x={pos.x} y={pos.y + 14} textAnchor="middle" style={{ fontSize: 12, fill: '#23364a' }}>
                {node.label.length > 16 ? `${node.label.slice(0, 16)}...` : node.label}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

const IndustryQAAgentPage = () => {
  const [searchParams] = useSearchParams()
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState('')
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [creating, setCreating] = useState(false)
  const [sending, setSending] = useState(false)
  const [trace, setTrace] = useState(null)
  const [qaStrategy, setQaStrategy] = useState('compare')
  const navigate = useNavigate()

  const incomingQuestion = String(searchParams.get('question') || '').trim()
  const incomingTraceId = String(searchParams.get('trace_id') || '').trim()
  const incomingStatementId = String(searchParams.get('statement_id') || '').trim()
  const incomingDocId = String(searchParams.get('doc_id') || '').trim()
  const releaseContext = useMemo(() => parseReleaseContext(searchParams), [searchParams])

  const activeSession = useMemo(
    () => sessions.find((item) => item.session_id === activeSessionId) || null,
    [sessions, activeSessionId],
  )

  const assistantMessages = useMemo(
    () => messages.filter((item) => item.role === 'assistant'),
    [messages],
  )

  const activeAssistantMessage = assistantMessages[assistantMessages.length - 1] || null
  const citations = activeAssistantMessage?.citations || []
  const retrievalCompare = trace?.retrieval_compare || activeAssistantMessage?.retrieval_compare || null
  const graphPathView = trace?.graph_path_view || activeAssistantMessage?.graph_path_view || null
  const answerMode = trace?.query_plan?.answer_mode || activeAssistantMessage?.answer_mode || 'classic'
  const retrievalHits = trace?.retrieval_hits || []
  const tablesUsed = trace?.tables_used || []
  const dataSources = trace?.data_sources || []
  const workflowReference = trace?.workflow_reference || null
  const qaRuntime = trace?.industry_qa || null
  const reasoningPath = trace?.reasoning_path || []
  const modelUsage = trace?.model_usage || null
  const openspgCompare = retrievalCompare?.openspg || {}
  const classicCompare = retrievalCompare?.classic || {}
  const openspgHits = openspgCompare?.hits || []
  const classicHits = classicCompare?.hits || []
  const graphLabels = openspgCompare?.graph_labels || []
  const reasonCandidates = openspgCompare?.reason_candidates || []
  const searchQueries = openspgCompare?.search_queries || []
  const searchChecks = openspgCompare?.search_checks || []
  const traceOverview = useMemo(() => buildTraceOverview(trace), [trace])
  const graphModel = useMemo(
    () => buildOpenSpgGraphModel({
      query: trace?.query_plan?.query || question || '',
      openspgHits,
      graphPathView,
    }),
    [trace, question, openspgHits, graphPathView],
  )

  const answerModeLabel = {
    openspg: 'OpenSPG增强回答',
    classic: '传统检索回答',
    classic_fallback: '传统检索回退',
  }[answerMode] || answerMode

  const citationColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '来源', dataIndex: 'source_name', key: 'source_name', width: 120 },
    { title: 'statement_id', dataIndex: 'statement_id', key: 'statement_id', width: 160 },
    { title: '发布时间', dataIndex: 'publish_time', key: 'publish_time', width: 180 },
    {
      title: '联动',
      key: 'action',
      width: 120,
      render: (_, row) => (
        <Button
          size="small"
          onClick={() => {
            if (!workflowReference?.run_id) return
            const params = new URLSearchParams({
              run_id: workflowReference.run_id,
              step: 'apply',
              open_detail: '1',
            })
            navigate(`/workflow?${params.toString()}`)
          }}
          disabled={!workflowReference?.run_id}
        >
          查看流程
        </Button>
      ),
    },
  ]

  const retrievalColumns = [
    { title: 'event_id', dataIndex: 'event_id', key: 'event_id', width: 160 },
    { title: '命中标题', dataIndex: 'headline_title', key: 'headline_title', ellipsis: true },
    { title: 'score', dataIndex: 'score', key: 'score', width: 100 },
  ]

  const compareColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: '类型', dataIndex: 'label', key: 'label', width: 160 },
    { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true },
    { title: 'score', dataIndex: 'score', key: 'score', width: 100 },
  ]

  const loadSessions = async () => {
    setLoadingSessions(true)
    try {
      const data = await industryQaApi.getSessions()
      const sessionList = Array.isArray(data?.sessions) ? data.sessions : []
      setSessions(sessionList)
      if (!activeSessionId && sessionList.length > 0) {
        setActiveSessionId(sessionList[0].session_id)
      }
    } catch (error) {
      message.error(`读取会话失败: ${error.message}`)
      setSessions([])
    } finally {
      setLoadingSessions(false)
    }
  }

  const loadMessages = async (sessionId) => {
    if (!sessionId) return
    setLoadingMessages(true)
    try {
      const data = await industryQaApi.getMessages(sessionId)
      const messageList = Array.isArray(data?.messages) ? data.messages : []
      setMessages(messageList)
      return messageList
    } catch (error) {
      message.error(`读取消息失败: ${error.message}`)
      setMessages([])
      return []
    } finally {
      setLoadingMessages(false)
    }
  }

  const createSession = async () => {
    setCreating(true)
    try {
      const payload = await industryQaApi.createSession({
        doc_type: 'news',
        title: releaseContext.hasReleaseContext
          ? `知识发布会话 ${releaseContext.releaseVersion || releaseContext.releaseId}`
          : undefined,
      })
      const sessionId = payload?.session_id
      await loadSessions()
      if (sessionId) {
        setActiveSessionId(sessionId)
        setMessages([])
      }
    } catch (error) {
      message.error(`创建会话失败: ${error.message}`)
    } finally {
      setCreating(false)
    }
  }

  const deleteSession = async (sessionId) => {
    if (!sessionId) return
    try {
      await industryQaApi.deleteSession(sessionId)
      const remaining = sessions.filter((item) => item.session_id !== sessionId)
      setSessions(remaining)
      if (activeSessionId === sessionId) {
        const nextSessionId = remaining[0]?.session_id || ''
        setActiveSessionId(nextSessionId)
        if (!nextSessionId) {
          setMessages([])
          setTrace(null)
        }
      }
      message.success('会话已删除')
    } catch (error) {
      message.error(`删除会话失败: ${error.message}`)
    }
  }

  const sendQuestion = async () => {
    const text = String(question || '').trim()
    if (!text) {
      message.warning('请输入问题')
      return
    }
    if (!activeSessionId) {
      message.warning('请先创建会话')
      return
    }

    const userQuestion = text
    setSending(true)
    setQuestion('')
    try {
      const sessionId = activeSessionId
      const metaRef = { trace_id: '', run_id: '' }
      setMessages((prev) => ([
        ...prev,
        {
          message_id: `local_user_${Date.now()}`,
          session_id: sessionId,
          role: 'user',
          content: userQuestion,
        },
        {
          message_id: `local_assistant_${Date.now()}`,
          session_id: sessionId,
          role: 'assistant',
          content: buildAssistantPlaceholder('processing'),
          trace_id: '',
          answer_mode: qaStrategy === 'openspg' ? 'openspg' : 'classic',
          retrieval_compare: null,
          citations: [],
        },
      ]))
      await industryQaApi.chatStream({
        session_id: activeSessionId,
        question: text,
        top_k: 10,
        filters: {
          hours: 24,
          qa_strategy: qaStrategy,
          release_id: releaseContext.releaseId || undefined,
          release_version: releaseContext.releaseVersion || undefined,
        },
      }, {
        onMeta: (payload) => {
          metaRef.trace_id = payload.trace_id || ''
          metaRef.run_id = payload.run_id || ''
          setMessages((prev) => {
            const next = [...prev]
            const target = next[next.length - 1]
            if (target?.role === 'assistant') {
              target.trace_id = payload.trace_id || ''
              target.answer_mode = payload.answer_mode || target.answer_mode || 'classic'
              if (!target.content || target.content === buildAssistantPlaceholder('processing') || target.content === buildAssistantPlaceholder('retrieving') || target.content === buildAssistantPlaceholder('answering')) {
                target.content = buildAssistantPlaceholder(payload.status || 'processing')
              }
            }
            return next
          })
        },
        onDelta: (payload) => {
          setMessages((prev) => {
            const next = [...prev]
            const target = next[next.length - 1]
            if (target?.role === 'assistant') {
              const current = String(target.content || '')
              const isPlaceholder = [
                buildAssistantPlaceholder('processing'),
                buildAssistantPlaceholder('retrieving'),
                buildAssistantPlaceholder('answering'),
                buildAssistantPlaceholder('default'),
              ].includes(current)
              target.content = isPlaceholder ? String(payload.content || '') : `${current}${payload.content || ''}`
            }
            return next
          })
        },
        onDone: async (payload) => {
          setMessages((prev) => {
            const next = [...prev]
            const target = next[next.length - 1]
            if (target?.role === 'assistant') {
              target.content = payload.answer || target.content || ''
              target.trace_id = payload.trace_id || target.trace_id || ''
              target.answer_mode = payload.answer_mode || target.answer_mode || 'classic'
              target.retrieval_compare = payload.retrieval_compare || target.retrieval_compare || null
              target.graph_path_view = payload.graph_path_view || target.graph_path_view || null
              target.citations = payload.citations || []
            }
            return next
          })
          const latestMessages = await loadMessages(sessionId)
          const assistantMessage = latestMessages.filter((item) => item.role === 'assistant').slice(-1)[0]
          if (assistantMessage?.message_id) {
            const traceData = await industryQaApi.getMessageTrace(assistantMessage.message_id)
            setTrace(traceData || null)
          }
        },
      })
    } catch (error) {
      setQuestion(userQuestion)
      message.error(`问答失败: ${error.message}`)
      await loadMessages(activeSessionId)
    } finally {
      setSending(false)
    }
  }

  const loadTraceByMessage = async (messageId) => {
    if (!messageId) return
    try {
      const data = await industryQaApi.getMessageTrace(messageId)
      setTrace(data || null)
    } catch (error) {
      message.error(`读取 Trace 失败: ${error.message}`)
    }
  }

  const loadTraceByTraceId = async (traceId) => {
    const id = String(traceId || '').trim()
    if (!id) return
    try {
      const data = await openApiService.getTrace(id)
      setTrace(data || null)
    } catch (error) {
      message.error(`读取 Trace 失败: ${error.message}`)
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  useEffect(() => {
    if (activeSessionId) {
      loadMessages(activeSessionId)
      setTrace(null)
    }
  }, [activeSessionId])

  useEffect(() => {
    if (incomingQuestion) {
      setQuestion(incomingQuestion)
    }
    if (incomingTraceId) {
      loadTraceByTraceId(incomingTraceId)
    }
  }, [incomingQuestion, incomingTraceId])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space direction="vertical" size={4}>
          <Space>
            <MessageOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
            <Title level={3} style={{ margin: 0 }}>产业动态问答智能体</Title>
            <Tag color="blue">Internal Demo</Tag>
          </Space>
          <Text type="secondary">
            该页用于平台能力展示与联调。外部生产应用请对接 `/api/v1/open/*` 接口。
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
        <Col xs={24} xl={5}>
          <Card
            title="会话列表"
            extra={<Button icon={<PlusOutlined />} onClick={createSession} loading={creating} />}
            bodyStyle={{ padding: 8 }}
          >
            <List
              loading={loadingSessions}
              dataSource={sessions}
              locale={{ emptyText: <Empty description="暂无会话" /> }}
              renderItem={(item) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    borderRadius: 8,
                    padding: '8px 10px',
                    background: item.session_id === activeSessionId ? '#ecf6fb' : 'transparent',
                    border: item.session_id === activeSessionId ? '1px solid #b5deef' : '1px solid transparent',
                  }}
                  onClick={() => setActiveSessionId(item.session_id)}
                >
                  <List.Item.Meta
                    title={<Text strong>{item.title || item.session_id}</Text>}
                    description={<Text type="secondary" style={{ fontSize: 12 }}>{item.doc_type || 'news'}</Text>}
                  />
                  <Button
                    size="small"
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(event) => {
                      event.stopPropagation()
                      deleteSession(item.session_id)
                    }}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} xl={19}>
          <Card title="问答对话" bodyStyle={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{
              minHeight: 420,
              maxHeight: 520,
              overflow: 'auto',
              border: '1px solid #dbe5ef',
              borderRadius: 10,
              padding: 12,
              background: '#f8fbfe',
            }}>
              <List
                loading={loadingMessages}
                dataSource={messages}
                locale={{ emptyText: <Empty description="暂无消息" /> }}
                renderItem={(item) => (
                  <List.Item
                    onClick={() => item.role === 'assistant' && loadTraceByMessage(item.message_id)}
                    style={{
                      display: 'block',
                      border: item.role === 'assistant' ? '1px solid #d9ebf5' : '1px solid #e7e9ee',
                      borderRadius: 8,
                      background: item.role === 'assistant' ? '#ffffff' : '#f3f5f8',
                      marginBottom: 10,
                      padding: 10,
                      cursor: item.role === 'assistant' ? 'pointer' : 'default'
                    }}
                  >
                    <Space style={{ marginBottom: 6 }}>
                      <Tag color={item.role === 'assistant' ? 'blue' : 'default'}>{item.role}</Tag>
                      {item.trace_id ? <Tag color="processing">{item.trace_id}</Tag> : null}
                    </Space>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{item.content}</div>
                  </List.Item>
                )}
              />
            </div>

            <Space direction="vertical" size={10} style={{ width: '100%' }}>
              <TextArea
                rows={4}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="例如：本周机器人产业链最值得关注的变化有哪些？"
              />
              <Space align="center" wrap>
                <Text type="secondary">问答策略</Text>
                <Segmented
                  value={qaStrategy}
                  onChange={(value) => setQaStrategy(String(value))}
                  options={[
                    { label: '自动对比', value: 'compare' },
                    { label: 'OpenSPG增强', value: 'openspg' },
                    { label: '传统检索', value: 'classic' },
                  ]}
                />
              </Space>
              <Space>
                <Button type="primary" icon={<SendOutlined />} onClick={sendQuestion} loading={sending}>发送问题</Button>
                <Button onClick={() => loadMessages(activeSessionId)} disabled={!activeSessionId}>刷新消息</Button>
              </Space>
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="证据与追踪" bodyStyle={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <Text strong>当前会话</Text>
          <div style={{ marginTop: 6 }}>
            {activeSession ? <Tag color="cyan">{activeSession.session_id}</Tag> : <Text type="secondary">未选择</Text>}
            {releaseContext.hasReleaseContext ? (
              <Space wrap style={{ marginTop: 8 }}>
                <Tag color="blue">release_id: {releaseContext.releaseId}</Tag>
                {releaseContext.releaseVersion ? <Tag color="purple">version: {releaseContext.releaseVersion}</Tag> : null}
              </Space>
            ) : null}
          </div>
        </div>

        <div>
          <Text strong>回答模式</Text>
          <div style={{ marginTop: 8 }}>
            <Space wrap>
              <Tag color={answerMode === 'openspg' ? 'green' : answerMode === 'classic_fallback' ? 'orange' : 'blue'}>
                {answerModeLabel}
              </Tag>
              {retrievalCompare?.strategy ? <Tag color="geekblue">strategy: {retrievalCompare.strategy}</Tag> : null}
              {openspgCompare?.status ? (
                <Tag color={openspgCompare.status === 'live' ? 'green' : openspgCompare.status === 'empty' ? 'gold' : 'default'}>
                  openspg: {openspgCompare.status}
                </Tag>
              ) : null}
            </Space>
          </div>
        </div>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <div style={traceCardStyle}>
              <Text strong>Workflow 关联</Text>
              <Descriptions
                size="small"
                column={1}
                style={{ marginTop: 12 }}
                items={traceOverview.workflowItems.map((item) => ({
                  key: item.label,
                  label: item.label,
                  children: item.value,
                }))}
              />
              {!workflowReference?.run_id ? (
                <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
                  当前 trace 还没有明确关联到某次 workflow run，优先展示问答运行时上下文。
                </Text>
              ) : null}
            </div>
          </Col>

          <Col xs={24} lg={8}>
            <div style={traceCardStyle}>
              <Text strong>实际使用的数据表 / 集合</Text>
              <Descriptions
                size="small"
                column={1}
                style={{ marginTop: 12 }}
                items={traceOverview.dataItems.map((item) => ({
                  key: item.label,
                  label: item.label,
                  children: item.value,
                }))}
              />
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  {tablesUsed.map((item) => (
                    <Tag color="blue" key={`${item.table}-${item.role}`}>{item.table}</Tag>
                  ))}
                  {qaRuntime?.collections_written?.map((item) => (
                    <Tag color="gold" key={item}>{item}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          </Col>

          <Col xs={24} lg={8}>
            <div style={traceCardStyle}>
              <Text strong>分析过程</Text>
              <Descriptions
                size="small"
                column={1}
                style={{ marginTop: 12 }}
                items={traceOverview.analysisItems.map((item) => ({
                  key: item.label,
                  label: item.label,
                  children: item.value,
                }))}
              />
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  {traceOverview.analysisSteps.map((item) => (
                    <Tag color="purple" key={item}>{item}</Tag>
                  ))}
                </Space>
              </div>
            </div>
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Text strong>OpenSPG Graph / Reason / Search</Text>
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div>
                <Text type="secondary">图谱视图</Text>
                <div style={{ marginTop: 8 }}>
                  <OpenSpgGraphPreview model={graphModel} />
                </div>
              </div>
              <div>
                <Text type="secondary">Graph / Reason 概览</Text>
                <div style={{ marginTop: 6 }}>
                  <Space wrap>
                    {graphLabels.map((item) => (
                      <Tag color="purple" key={item}>{item}</Tag>
                    ))}
                    {reasonCandidates.map((item) => (
                      <Tag color="magenta" key={`${item.label}-${item.name}`}>{item.name_zh || item.name}</Tag>
                    ))}
                  </Space>
                </div>
              </div>
              <div>
                <Collapse
                  items={[
                    {
                      key: 'searchQueries',
                      label: '查看查询语句与执行状态',
                      children: (
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          {searchQueries.map((item, index) => {
                            const check = searchChecks[index] || {}
                            return (
                              <div
                                key={`${index}-${item}`}
                                style={{
                                  fontSize: 12,
                                  lineHeight: 1.5,
                                  background: '#f6f9fc',
                                  border: '1px solid #dbe5ef',
                                  borderRadius: 8,
                                  padding: 8,
                                }}
                              >
                                <div>{item}</div>
                                <Text type="secondary">kind={check.kind || '-'} mode={check.mode || '-'} status={check.http_status || '-'}</Text>
                              </div>
                            )
                          })}
                        </Space>
                      ),
                    },
                  ]}
                />
              </div>
              <div>
                <Text type="secondary">OpenSPG 增强命中</Text>
                <Table
                  size="small"
                  rowKey={(row, idx) => row.id || idx}
                  pagination={false}
                  scroll={{ x: 720 }}
                  style={{ marginTop: 8 }}
                  dataSource={openspgHits}
                  columns={compareColumns}
                  locale={{ emptyText: openspgCompare?.status === 'empty' ? '已真实调用 OpenSPG，但当前图谱暂无直接命中' : '暂无 OpenSPG 命中' }}
                />
              </div>
            </div>
          </Col>

          <Col xs={24} lg={12}>
            <Text strong>传统检索命中</Text>
            <Table
              size="small"
              rowKey={(row, idx) => row.id || row.event_id || idx}
              pagination={false}
              scroll={{ x: 720 }}
              style={{ marginTop: 8 }}
              dataSource={classicHits.length > 0 ? classicHits : retrievalHits}
              columns={classicHits.length > 0 ? compareColumns : retrievalColumns}
              locale={{ emptyText: '暂无命中' }}
            />
          </Col>
        </Row>

        <div>
          <Text strong>引用证据</Text>
          <Table
            size="small"
            rowKey={(row, idx) => row.doc_id || idx}
            pagination={false}
            scroll={{ x: 720 }}
            style={{ marginTop: 8 }}
            dataSource={citations}
            columns={citationColumns}
            locale={{ emptyText: '暂无证据' }}
          />
        </div>

        <div>
          <Text strong>Trace</Text>
          {trace ? (
            <>
              <Divider style={{ margin: '8px 0 12px' }} />
              <Collapse
                items={[
                  {
                    key: 'trace',
                    label: '查看原始 Trace JSON',
                    children: (
                      <pre style={{
                        margin: 0,
                        maxHeight: 260,
                        overflow: 'auto',
                        background: '#f6f9fc',
                        border: '1px solid #dbe5ef',
                        borderRadius: 8,
                        padding: 10,
                        fontSize: 12,
                        lineHeight: 1.45,
                        whiteSpace: 'pre-wrap'
                      }}>
                        {JSON.stringify(trace, null, 2)}
                      </pre>
                    ),
                  },
                ]}
              />
            </>
          ) : <Empty description="点击助手消息查看 trace" />}
        </div>
      </Card>
    </div>
  )
}

export default IndustryQAAgentPage
