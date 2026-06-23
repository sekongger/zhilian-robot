import React from 'react'
import { Card, Space, Tag, Typography } from 'antd'
import { BuildOutlined } from '@ant-design/icons'
import OpenSPGModelStudioPage from './OpenSPGModelStudioPage'

const { Title, Text } = Typography

const ModelStudioPage = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card>
        <Space direction="vertical" size={6}>
          <Space>
            <BuildOutlined style={{ color: '#0b6e99', fontSize: 20 }} />
            <Title level={3} style={{ margin: 0 }}>模型管理</Title>
            <Tag color="geekblue">Schema + KAG</Tag>
          </Space>
          <Text type="secondary">
            统一管理 Schema 提交与激活、抽取任务提交、状态追踪与样本检查。
          </Text>
        </Space>
      </Card>
      <OpenSPGModelStudioPage />
    </div>
  )
}

export default ModelStudioPage
