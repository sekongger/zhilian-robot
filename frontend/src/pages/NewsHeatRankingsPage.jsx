import React, { useEffect, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Empty,
  Progress,
  Radio,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import {
  FireOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import newsGraphApi from '../services/newsGraphApi'
import {
  ENTITY_HEAT_TYPE_OPTIONS,
  PERIOD_OPTIONS,
  buildHeatRankingQueryParams,
  buildFormulaRows,
  formatHeatScore,
  getEntityTypeLabel,
  normalizeRankingResponse,
} from './newsHeatRankingsModel.mjs'

const { Title, Text, Paragraph } = Typography

const cardStyle = {
  borderRadius: 18,
  border: '1px solid rgba(11, 110, 153, 0.14)',
  boxShadow: '0 14px 32px rgba(15, 40, 65, 0.08)',
}

function EvidenceList({ items = [] }) {
  if (!items.length) {
    return <Text type="secondary">暂无证据资讯</Text>
  }
  return (
    <Space direction="vertical" size={4}>
      {items.slice(0, 3).map((item, index) => (
        <a
          key={`${item.url || item.title || index}`}
          href={item.url || '#'}
          target="_blank"
          rel="noreferrer"
          style={{ maxWidth: 360, display: 'block' }}
        >
          <Text ellipsis style={{ maxWidth: 360 }}>
            {item.title || item.url || '未命名资讯'}
          </Text>
        </a>
      ))}
    </Space>
  )
}

function FormulaCard({ formula }) {
  const rows = buildFormulaRows(formula)
  return (
    <Card style={cardStyle}>
      <Space direction="vertical" size={14} style={{ width: '100%' }}>
        <Space>
          <ThunderboltOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
          <Title level={4} style={{ margin: 0 }}>热度计算公式</Title>
        </Space>
        <Paragraph style={{ marginBottom: 0, color: 'var(--text-secondary)' }}>
          heat_score = 100 * (0.45 * 提及强度 + 0.20 * 关联资讯热度 + 0.15 * 来源覆盖度 + 0.10 * 时间新鲜度 + 0.10 * 锚点可信度)
        </Paragraph>
        <Descriptions bordered column={1} size="small">
          {rows.map((item) => (
            <Descriptions.Item
              key={item.key}
              label={<Space><Tag color="blue">{item.weightText}</Tag>{item.name}</Space>}
            >
              {item.description}
            </Descriptions.Item>
          ))}
        </Descriptions>
      </Space>
    </Card>
  )
}

export default function NewsHeatRankingsPage() {
  const { message } = App.useApp()
  const [periodType, setPeriodType] = useState('daily')
  const [entityType, setEntityType] = useState('Enterprise')
  const [date, setDate] = useState(null)
  const [payload, setPayload] = useState(() => normalizeRankingResponse())
  const [loading, setLoading] = useState(false)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState('')

  const loadRankings = async () => {
    setLoading(true)
    setError('')
    try {
      const result = await newsGraphApi.getHeatRankings(
        buildHeatRankingQueryParams({
          periodType,
          date,
          entityType,
          limit: 50,
        }),
      )
      const normalized = normalizeRankingResponse(result)
      setPayload(normalized)
      if (!date && normalized.period_start) {
        setDate(dayjs(normalized.period_start))
      }
    } catch (err) {
      setError(err.message || '读取热度榜失败')
      setPayload(normalizeRankingResponse({ period_type: periodType, entity_type: entityType, items: [] }))
    } finally {
      setLoading(false)
    }
  }

  const calculateRankings = async () => {
    setCalculating(true)
    setError('')
    try {
      const result = await newsGraphApi.calculateHeatRankings({
        period_type: periodType,
        as_of: (date || dayjs()).format('YYYY-MM-DD'),
        entity_type: entityType,
        limit_per_type: 50,
      })
      const rankingPayload = result?.result || result
      const normalized = normalizeRankingResponse(rankingPayload)
      setPayload(normalized)
      if (normalized.period_start) {
        setDate(dayjs(normalized.period_start))
      }
      message.success('热度榜快照已生成')
    } catch (err) {
      setError(err.message || '触发热度榜计算失败')
    } finally {
      setCalculating(false)
    }
  }

  useEffect(() => {
    loadRankings()
  }, [periodType, entityType, date])

  const columns = [
    {
      title: '排名',
      dataIndex: 'rank',
      width: 78,
      render: (rank) => <Tag color={rank <= 3 ? 'volcano' : 'blue'}>#{rank}</Tag>,
    },
    {
      title: '实体',
      dataIndex: 'entity_name',
      render: (name, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{name}</Text>
          <Space wrap size={4}>
            {(record.entity_labels || []).filter((label) => label !== 'Entity').map((label) => (
              <Tag key={label}>{label}</Tag>
            ))}
          </Space>
        </Space>
      ),
    },
    {
      title: '热度分',
      dataIndex: 'heat_score',
      width: 190,
      sorter: (a, b) => Number(a.heat_score || 0) - Number(b.heat_score || 0),
      render: (score) => (
        <Space direction="vertical" size={2} style={{ width: 150 }}>
          <Text strong>{formatHeatScore(score)}</Text>
          <Progress percent={Math.min(Number(score || 0), 100)} showInfo={false} strokeColor="#0b6e99" />
        </Space>
      ),
    },
    {
      title: '提及/来源',
      width: 130,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Text>{record.mention_count || 0} 篇资讯</Text>
          <Text type="secondary">{record.source_count || 0} 个来源</Text>
        </Space>
      ),
    },
    {
      title: '锚点',
      width: 190,
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Tag color={record.anchor_score >= 1 ? 'green' : record.anchor_score >= 0.6 ? 'gold' : 'default'}>
            anchor {formatHeatScore(record.anchor_score)}
          </Tag>
          <Text type="secondary" ellipsis style={{ maxWidth: 160 }}>
            {record.anchor_id || '未匹配常识锚点'}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Top 证据资讯',
      dataIndex: 'top_evidence',
      render: (items) => <EvidenceList items={items} />,
    },
  ]

  return (
    <Space direction="vertical" size={18} style={{ width: '100%' }}>
      <Card
        style={{
          ...cardStyle,
          background: 'linear-gradient(135deg, rgba(11,110,153,0.10) 0%, rgba(47,158,68,0.08) 100%)',
        }}
      >
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Space align="start" style={{ justifyContent: 'space-between', width: '100%' }}>
            <Space direction="vertical" size={4}>
              <Space>
                <FireOutlined style={{ color: '#d94841', fontSize: 24 }} />
                <Title level={2} style={{ margin: 0 }}>资讯实体热度榜</Title>
              </Space>
              <Text type="secondary">
                基于 Graphiti 资讯图谱生成每日/每周人物、产品、公司、技术等实体热度快照，作为资讯推荐和产业简报的副产物。
              </Text>
            </Space>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadRankings} loading={loading}>
                刷新
              </Button>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={calculateRankings} loading={calculating}>
                重新计算快照
              </Button>
            </Space>
          </Space>

          <Space wrap>
            <Radio.Group
              optionType="button"
              buttonStyle="solid"
              value={periodType}
              options={PERIOD_OPTIONS}
              onChange={(event) => {
                setPeriodType(event.target.value)
                setDate(null)
              }}
            />
            <DatePicker value={date} onChange={(value) => setDate(value)} allowClear />
            <Button onClick={() => setDate(null)}>最近快照</Button>
            <Radio.Group
              optionType="button"
              value={entityType}
              options={ENTITY_HEAT_TYPE_OPTIONS.map((item) => ({ label: item.label, value: item.value }))}
              onChange={(event) => {
                setEntityType(event.target.value)
                setDate(null)
              }}
            />
          </Space>
        </Space>
      </Card>

      {error ? <Alert type="error" showIcon message={error} /> : null}

      <FormulaCard formula={payload.formula} />

      <Card
        title={`${PERIOD_OPTIONS.find((item) => item.value === periodType)?.label || '热度榜'} · ${getEntityTypeLabel(entityType)}`}
        extra={<Text type="secondary">{payload.period_start || '-'} 至 {payload.period_end || '-'}</Text>}
        style={cardStyle}
      >
        <Table
          rowKey={(record) => record.entity_uuid || `${record.entity_name}-${record.rank}`}
          columns={columns}
          dataSource={payload.items}
          loading={loading || calculating}
          pagination={{ pageSize: 10, showSizeChanger: true }}
          locale={{ emptyText: <Empty description="暂无热度榜快照，可点击重新计算快照" /> }}
        />
      </Card>
    </Space>
  )
}
