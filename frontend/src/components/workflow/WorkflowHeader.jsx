import React from 'react'
import { Card, Space, Tag, Typography } from 'antd'
import { PartitionOutlined } from '@ant-design/icons'

const { Title, Text } = Typography

const STATUS_COLOR = {
  queued: 'default',
  running: 'processing',
  success: 'success',
  failed: 'error',
  partial_success: 'warning',
}

const PROFILE_COLOR = {
  kag_openspg: 'blue',
  openks_direct: 'geekblue',
}

const WorkflowHeader = ({ runId, status, runtimeProfile }) => {
  return (
    <Card>
      <Space direction="vertical" size={6}>
        <Space>
          <PartitionOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
          <Title level={3} style={{ margin: 0 }}>资讯全流程工作台</Title>
          <Tag color={PROFILE_COLOR[runtimeProfile] || 'blue'}>{`${runtimeProfile || 'kag_openspg'} 主链`}</Tag>
          {status ? <Tag color={STATUS_COLOR[status] || 'default'}>{status}</Tag> : null}
        </Space>
        <Text type="secondary">
          统一执行 OpenKS schema 适配、资讯接入、KAG bridge、Builder 与图物化六阶段，并将结果绑定到统一 runtime 对象。
        </Text>
        {runId ? <Tag color="processing">run_id: {runId}</Tag> : null}
      </Space>
    </Card>
  )
}

export default WorkflowHeader
