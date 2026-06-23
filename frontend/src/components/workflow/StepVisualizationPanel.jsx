import React from 'react'
import { Card, Col, Empty, Row, Statistic, Timeline } from 'antd'
import D3ForceGraph from '../D3ForceGraph'

const STATUS_COLOR = {
  finish: 'green',
  error: 'red',
  process: 'blue',
  wait: 'gray',
}

const StepVisualizationPanel = ({ visualization }) => {
  const type = visualization?.type || 'none'
  const title = visualization?.title || '可视化'
  const data = visualization?.data || {}

  if (type === 'graph') {
    if (!Array.isArray(data?.nodes) || data.nodes.length === 0) {
      return <Empty description="暂无图谱数据" />
    }
    return (
      <div style={{ minHeight: 420 }}>
        <D3ForceGraph data={{ nodes: data.nodes, edges: data.edges || [] }} />
      </div>
    )
  }

  if (type === 'timeline') {
    const items = (data?.items || []).map((item) => ({
      color: STATUS_COLOR[item.status] || 'blue',
      children: (
        <div>
          <div style={{ fontWeight: 600 }}>{item.label || '-'}</div>
          <div style={{ color: '#64748b', fontSize: 12 }}>{item.description || '-'}</div>
        </div>
      ),
    }))
    return items.length > 0 ? <Timeline items={items} /> : <Empty description="暂无时间线数据" />
  }

  if (type === 'stats') {
    const items = data?.items || []
    return items.length > 0 ? (
      <Row gutter={[12, 12]}>
        {items.map((item) => (
          <Col xs={12} md={8} key={item.label}>
            <Card size="small">
              <Statistic title={item.label} value={item.value} valueStyle={{ fontSize: 18 }} />
            </Card>
          </Col>
        ))}
      </Row>
    ) : <Empty description="暂无统计数据" />
  }

  return <Empty description={`${title}暂无可视化内容`} />
}

export default StepVisualizationPanel
