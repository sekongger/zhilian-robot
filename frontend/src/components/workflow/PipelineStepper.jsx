import React from 'react'
import { Card, Col, Progress, Row, Space, Tag, Typography } from 'antd'

const { Text } = Typography

const STATUS_META = {
  idle: { color: 'default', percent: 0, label: '待执行' },
  running: { color: 'processing', percent: 60, label: '执行中' },
  success: { color: 'success', percent: 100, label: '已完成' },
  partial_success: { color: 'warning', percent: 100, label: '部分成功' },
  failed: { color: 'error', percent: 100, label: '失败' },
}

const PipelineStepper = ({ steps, activeKey, onStepClick }) => {
  return (
    <Row gutter={[12, 12]}>
      {(steps || []).map((step, index) => {
        const meta = STATUS_META[step.status] || STATUS_META.idle
        const active = step.key === activeKey
        return (
          <Col xs={24} sm={12} lg={8} xl={4} key={step.key}>
            <Card
              size="small"
              hoverable={!!onStepClick}
              onClick={() => onStepClick?.(step.key)}
              style={{
                height: '100%',
                cursor: onStepClick ? 'pointer' : 'default',
                borderColor: active ? '#1677ff' : undefined,
                boxShadow: active ? '0 0 0 2px rgba(22,119,255,0.12)' : undefined,
              }}
            >
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                  <Text strong>{index + 1}. {step.title}</Text>
                  <Tag color={meta.color}>{meta.label}</Tag>
                </Space>
                <Text type="secondary" style={{ minHeight: 36 }}>{step.desc}</Text>
                <Progress percent={meta.percent} size="small" status={step.status === 'failed' ? 'exception' : 'active'} />
              </Space>
            </Card>
          </Col>
        )
      })}
    </Row>
  )
}

export default PipelineStepper
