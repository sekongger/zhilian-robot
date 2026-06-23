import React from 'react'
import { Button, Card, Space, Statistic, Tag, Typography } from 'antd'
import { FilterOutlined } from '@ant-design/icons'

const { Text } = Typography

const StepProcessPanel = ({ loading, result, error, onRun }) => {
  const preview = result?.preview || {}
  const status = result?.status || {}
  const rowCount = preview?.meta?.row_count ?? preview?.row_count ?? 0
  const lineCount = preview?.meta?.jsonl_line_count ?? preview?.jsonl_line_count ?? 0
  const cursorText = typeof status?.cursor === 'string'
    ? status.cursor
    : status?.cursor?.last_seen_time || '-'

  return (
    <Card title="Step3 处理" size="small" extra={<Button icon={<FilterOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">标准化批次并生成预览，更新 bridge 状态。</Text>
        {result ? (
          <Space wrap>
            <Statistic title="记录数" value={rowCount} valueStyle={{ fontSize: 18 }} />
            <Statistic title="JSONL" value={lineCount} valueStyle={{ fontSize: 18 }} />
            <Tag color="processing">cursor: {cursorText}</Tag>
          </Space>
        ) : <Tag>尚未执行</Tag>}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepProcessPanel
