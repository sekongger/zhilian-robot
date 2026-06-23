import React from 'react'
import { Button, Card, Empty, List, Space, Tag, Typography } from 'antd'
import { CloudUploadOutlined, DeploymentUnitOutlined, EyeOutlined } from '@ant-design/icons'

const { Paragraph, Text } = Typography

const PublishedPipelinePanel = ({
  pipelines = [],
  selectedPipelineKey = '',
  onSelectPipeline,
  onLoadPipeline,
}) => {
  return (
    <Card
      title="Pipeline 发布展示"
      extra={
        <Space size={6}>
          <CloudUploadOutlined style={{ color: '#0b6e99' }} />
          <Text type="secondary">{pipelines.length} 条</Text>
        </Space>
      }
      styles={{ body: { padding: 12 } }}
    >
      {pipelines.length === 0 ? (
        <Empty description="暂无已发布 pipeline" />
      ) : (
        <List
          dataSource={pipelines}
          renderItem={(pipeline) => {
            const selected = pipeline.key === selectedPipelineKey
            return (
              <List.Item style={{ paddingInline: 0, borderBlockEnd: 'none', paddingTop: 0, paddingBottom: 12 }}>
                <div
                  style={{
                    width: '100%',
                    borderRadius: 14,
                    border: selected ? '1px solid #1c7ed6' : '1px solid #d7e0ea',
                    background: selected
                      ? 'linear-gradient(180deg, rgba(28, 126, 214, 0.12) 0%, rgba(28, 126, 214, 0.04) 100%)'
                      : '#ffffff',
                    padding: 14,
                    boxShadow: selected ? '0 10px 24px rgba(28, 126, 214, 0.12)' : '0 6px 18px rgba(15, 40, 65, 0.04)',
                  }}
                >
                  <Space direction="vertical" size={10} style={{ width: '100%' }}>
                    <Space wrap style={{ justifyContent: 'space-between', width: '100%' }}>
                      <Space wrap>
                        <DeploymentUnitOutlined style={{ color: '#0b6e99' }} />
                        <Text strong style={{ color: '#14213d' }}>
                          {pipeline.name}
                        </Text>
                        <Tag color={pipeline.is_builtin ? 'blue' : 'green'}>
                          {pipeline.is_builtin ? '系统内置' : '用户发布'}
                        </Tag>
                      </Space>
                      <Space size={6}>
                        <Button size="small" icon={<EyeOutlined />} onClick={() => onSelectPipeline?.(pipeline.key)}>
                          查看
                        </Button>
                        <Button size="small" type="primary" onClick={() => onLoadPipeline?.(pipeline)}>
                          载入编排区
                        </Button>
                      </Space>
                    </Space>

                    <Paragraph style={{ marginBottom: 0, color: '#52607a' }} ellipsis={{ rows: 2 }}>
                      {pipeline.description || '未填写说明。'}
                    </Paragraph>

                    <Space wrap size={[6, 6]}>
                      {(pipeline.source_types || []).map((item) => (
                        <Tag key={item}>{item}</Tag>
                      ))}
                      <Tag color="geekblue">{(pipeline.operators || []).length} 个算子</Tag>
                      <Tag color="purple">发布者: {pipeline.published_by || 'system'}</Tag>
                    </Space>
                  </Space>
                </div>
              </List.Item>
            )
          }}
        />
      )}
    </Card>
  )
}

export default PublishedPipelinePanel
