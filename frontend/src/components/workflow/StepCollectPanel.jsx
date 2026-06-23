import React from 'react'
import { Button, Card, Space, Statistic, Tag, Typography } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'

const { Text } = Typography

const StepCollectPanel = ({ loading, result, error, onRun }) => {
  return (
    <Card title="Step2 采集" size="small" extra={<Button icon={<DownloadOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">从 RSS/API 拉取资讯并写入资源层。</Text>
        {result ? (
          <Space wrap>
            <Statistic title="新增" value={result.inserted_count || 0} valueStyle={{ fontSize: 18 }} />
            <Statistic title="采集源" value={result.feed_count || 0} valueStyle={{ fontSize: 18 }} />
            <Tag color="success">collect done</Tag>
          </Space>
        ) : <Tag>尚未执行</Tag>}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepCollectPanel
