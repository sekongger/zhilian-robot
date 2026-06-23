import React, { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  InputNumber,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message
} from 'antd'
import { ArrowLeftOutlined, ReloadOutlined, ApiOutlined } from '@ant-design/icons'
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

const JsonPanel = ({ title, data, height = 280 }) => (
  <Card title={title} size="small">
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

const OpenSPGKagHeadlineEventDetailPage = () => {
  const navigate = useNavigate()
  const { eventId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [loadingHealth, setLoadingHealth] = useState(false)
  const [eventDetail, setEventDetail] = useState(null)
  const [engineHealth, setEngineHealth] = useState(null)

  const hours = Number(searchParams.get('hours') || 24)
  const projectId = Number(searchParams.get('project_id') || 1)

  const loadDetail = async () => {
    if (!eventId) return
    setLoading(true)
    try {
      const data = await openspgDemoService.getHeadlineDetail(eventId, {
        hours,
        allow_demo_fallback: false
      })
      setEventDetail(data)
    } catch (error) {
      message.error(`加载事件详情失败: ${error.message}`)
      setEventDetail(null)
    } finally {
      setLoading(false)
    }
  }

  const loadEngineHealth = async () => {
    setLoadingHealth(true)
    try {
      const data = await openspgDemoService.getEngineHealth(projectId)
      setEngineHealth(data)
    } catch (error) {
      message.error(`加载引擎健康状态失败: ${error.message}`)
    } finally {
      setLoadingHealth(false)
    }
  }

  useEffect(() => {
    loadDetail()
    loadEngineHealth()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, hours, projectId])

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space wrap>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/openspg-kag-headlines')}>
            返回头条页
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            事件详情与证据追溯
          </Title>
          {eventDetail?.event_type && (
            <Tag color={EVENT_TYPE_COLOR[eventDetail.event_type] || 'default'}>
              {eventDetail?.event_type_zh || eventDetail?.event_type}
            </Tag>
          )}
        </Space>
        <Space wrap>
          <Text type="secondary">时间窗口(小时)</Text>
          <InputNumber
            min={6}
            max={168}
            step={6}
            value={hours}
            onChange={(v) => setSearchParams({ hours: String(v || 24), project_id: String(projectId) })}
          />
          <Text type="secondary">Project ID</Text>
          <InputNumber
            min={1}
            value={projectId}
            onChange={(v) => setSearchParams({ hours: String(hours), project_id: String(v || 1) })}
          />
          <Button icon={<ReloadOutlined />} onClick={loadDetail} loading={loading}>
            刷新事件
          </Button>
          <Button icon={<ApiOutlined />} onClick={loadEngineHealth} loading={loadingHealth}>
            刷新引擎状态
          </Button>
        </Space>
      </Space>

      <Alert
        type="info"
        showIcon
        message="演示闭环说明"
        description="本页展示产业头条事件的证据追溯（新闻原文片段/链接）以及 OpenSPG 查询提示，用于现场证明该头条并非黑盒生成。"
      />

      {loading && !eventDetail ? (
        <Card>
          <Spin />
        </Card>
      ) : !eventDetail ? (
        <Card>
          <Empty description="未找到事件详情" />
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={14}>
              <Card title={eventDetail.event_title || '事件概览'}>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="事件ID">{eventDetail.event_id}</Descriptions.Item>
                  <Descriptions.Item label="头条分">{eventDetail.headline_score}</Descriptions.Item>
                  <Descriptions.Item label="来源数">{eventDetail.source_count}</Descriptions.Item>
                  <Descriptions.Item label="证据数">
                    {(eventDetail.evidence_news || []).length}
                  </Descriptions.Item>
                  <Descriptions.Item label="首次时间">
                    {eventDetail.first_publish_time ? new Date(eventDetail.first_publish_time).toLocaleString() : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="最新时间">
                    {eventDetail.latest_publish_time ? new Date(eventDetail.latest_publish_time).toLocaleString() : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="涉及企业" span={2}>
                    <Space wrap>
                      {(eventDetail.companies || []).map((c) => (
                        <Tag key={c}>{c}</Tag>
                      ))}
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="数据源" span={2}>
                    {eventDetail?.meta?.data_source || 'unknown'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} xl={10}>
              <Card
                title="OpenSPG 接入状态"
                extra={
                  <Tag color={engineHealth?.status === 'live' ? 'success' : engineHealth?.status === 'partial' ? 'warning' : 'default'}>
                    {engineHealth?.status || 'unknown'}
                  </Tag>
                }
              >
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Text type="secondary">Base URL: {engineHealth?.openspg_base_url || 'http://127.0.0.1:8887'}</Text>
                  <Text type="secondary">
                    健康检查: {(engineHealth?.ok_count || 0)}/{engineHealth?.total_checks || 0}
                  </Text>
                  <Space wrap>
                    {Object.entries(engineHealth?.checks || {}).map(([name, check]) => (
                      <Tag key={name} color={check?.mode === 'live' && (check?.http_status || 0) < 400 ? 'success' : 'default'}>
                        {name}: {check?.mode || 'n/a'} {check?.http_status ? `(${check.http_status})` : ''}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              </Card>
            </Col>
          </Row>

          <Card title="证据新闻（可追溯到原文）">
            <Table
              rowKey="news_id"
              size="small"
              pagination={{ pageSize: 10 }}
              dataSource={eventDetail.evidence_news || []}
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
                  render: (value) => <Text type="secondary">{value || '-'}</Text>,
                  ellipsis: true
                },
                {
                  title: '发布时间',
                  dataIndex: 'publish_time',
                  width: 180,
                  render: (value) => (value ? new Date(value).toLocaleString() : '-')
                }
              ]}
            />
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <JsonPanel title="OpenSPG 查询提示（供引擎演示联调）" data={eventDetail.openspg_query_hints} height={220} />
            </Col>
            <Col xs={24} xl={12}>
              <JsonPanel title="事件原始数据(JSON)" data={eventDetail} height={220} />
            </Col>
          </Row>
        </>
      )}
    </Space>
  )
}

export default OpenSPGKagHeadlineEventDetailPage
