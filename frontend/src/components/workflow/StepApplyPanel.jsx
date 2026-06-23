import React from 'react'
import { Button, Card, Empty, List, Space, Tag, Typography } from 'antd'
import { AppstoreOutlined } from '@ant-design/icons'

const { Text } = Typography

const StepApplyPanel = ({ loading, result, error, onRun }) => {
  const headlines = result?.headlines || []

  return (
    <Card title="Step6 应用" size="small" extra={<Button icon={<AppstoreOutlined />} onClick={onRun} loading={loading}>执行</Button>}>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text type="secondary">读取应用快照，校验头条结果是否可用。</Text>
        {headlines.length === 0 ? (
          <Empty description="暂无头条结果" />
        ) : (
          <List
            size="small"
            dataSource={headlines.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <Text strong>{item.headline_title}</Text>
                  <Space wrap>
                    <Tag color="blue">score: {item.headline_score}</Tag>
                    <Tag color="cyan">sources: {item.source_count}</Tag>
                  </Space>
                </Space>
              </List.Item>
            )}
          />
        )}
        {error ? <Text type="danger">{error}</Text> : null}
      </Space>
    </Card>
  )
}

export default StepApplyPanel
