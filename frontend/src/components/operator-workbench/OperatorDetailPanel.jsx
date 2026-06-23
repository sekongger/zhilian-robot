import React from 'react'
import { Card, Descriptions, Divider, Empty, List, Space, Tag, Typography } from 'antd'
import { DatabaseOutlined, InfoCircleOutlined, NodeExpandOutlined } from '@ant-design/icons'

const { Paragraph, Text } = Typography

const formatSchemaType = (schema = {}) => {
  if (schema.type === 'array') {
    const inner = formatSchemaType(schema.items || {})
    return inner ? `array<${inner}>` : 'array'
  }
  if (schema.$ref) {
    return schema.$ref.split('/').pop()
  }
  if (Array.isArray(schema.anyOf) && schema.anyOf.length > 0) {
    return schema.anyOf.map((item) => formatSchemaType(item)).filter(Boolean).join(' | ')
  }
  return schema.type || 'object'
}

const schemaProperties = (schema = {}) =>
  Object.entries(schema.properties || {}).map(([name, property]) => ({
    name,
    type: formatSchemaType(property),
    description: property.description || '',
    required: Array.isArray(schema.required) ? schema.required.includes(name) : false,
  }))

const SchemaCard = ({ title, schema }) => {
  const properties = schemaProperties(schema)
  return (
    <Card
      size="small"
      title={title}
      styles={{ body: { padding: 12 } }}
      style={{ background: '#f8fbff', borderColor: '#d7e0ea' }}
    >
      {properties.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前 DTO 未声明一级字段" />
      ) : (
        <List
          size="small"
          dataSource={properties}
          renderItem={(item) => (
            <List.Item style={{ paddingInline: 0 }}>
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Space wrap>
                  <Text strong>{item.name}</Text>
                  <Tag color={item.required ? 'red' : 'default'}>{item.required ? 'required' : 'optional'}</Tag>
                  <Tag color="blue">{item.type}</Tag>
                </Space>
                {item.description ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {item.description}
                  </Text>
                ) : null}
              </Space>
            </List.Item>
          )}
        />
      )}
    </Card>
  )
}

const OperatorDetailPanel = ({ operator, layers = [] }) => {
  if (!operator) {
    return (
      <Card title="算子详情">
        <Empty description="请选择一个算子查看详情" />
      </Card>
    )
  }

  const layerMap = Object.fromEntries(layers.map((layer) => [layer.key, layer]))
  const categoryKey = operator.knowledge_category || operator.layer
  const categoryMeta = layerMap[categoryKey]
  const operatorClassLabel = operator.operator_class === 'business' ? '业务扩展' : '通用基础'

  return (
    <Card title="算子详情" styles={{ body: { padding: 16 } }}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <div
          style={{
            borderRadius: 14,
            padding: 16,
            background: 'linear-gradient(135deg, rgba(11, 110, 153, 0.08) 0%, rgba(28, 126, 214, 0.03) 100%)',
            border: '1px solid rgba(28, 126, 214, 0.14)',
          }}
        >
          <Space align="center" wrap>
            <InfoCircleOutlined style={{ color: '#0b6e99' }} />
            <Text strong style={{ fontSize: 16, color: '#14213d' }}>
              {operator.name}
            </Text>
            <Tag color="processing">{operator.stage}</Tag>
                  {operator.side_effect ? <Tag color="gold">副作用</Tag> : <Tag color="green">纯变换</Tag>}
                  <Tag color={operator.status === 'implemented' ? 'green' : 'gold'}>
                    {operator.status === 'implemented' ? '已实现' : '规划中'}
                  </Tag>
                  <Tag>{categoryMeta?.name || categoryKey}</Tag>
                  <Tag color={operator.operator_class === 'business' ? 'volcano' : 'blue'}>
                    {operatorClassLabel}
                  </Tag>
                  {operator.requires_schema ? <Tag color="purple">依赖 Schema</Tag> : null}
                  {operator.requires_llm ? <Tag color="magenta">依赖 LLM</Tag> : null}
                </Space>
          <Paragraph style={{ marginTop: 10, marginBottom: 0, color: '#52607a' }}>
            {operator.description}
          </Paragraph>
        </div>

        <Descriptions
          size="small"
          column={1}
          bordered
          items={[
            { key: 'impl', label: '实现映射', children: operator.implementation_ref },
            {
              key: 'layer',
              label: '知识计算目录',
              children: categoryMeta?.name || categoryKey,
            },
            {
              key: 'class',
              label: '算子类别',
              children: operatorClassLabel,
            },
            { key: 'input', label: '输入 DTO', children: operator.input_type },
            { key: 'output', label: '输出 DTO', children: operator.output_type },
            {
              key: 'sources',
              label: '适用来源',
              children: (
                <Space wrap>
                  {(operator.applicable_sources || []).map((source) => (
                    <Tag key={source}>{source}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              key: 'tags',
              label: '标签',
              children: (
                <Space wrap>
                  {(operator.tags || []).map((tag) => (
                    <Tag key={tag} color="blue">
                      {tag}
                    </Tag>
                  ))}
                </Space>
              ),
            },
          ]}
        />

        <Divider style={{ margin: '4px 0' }}>
          <Space>
            <DatabaseOutlined />
            DTO 结构
          </Space>
        </Divider>

        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <SchemaCard title={`输入: ${operator.input_type}`} schema={operator.input_schema || {}} />
          <SchemaCard title={`输出: ${operator.output_type}`} schema={operator.output_schema || {}} />
        </Space>

        <Divider style={{ margin: '4px 0' }}>
          <Space>
            <NodeExpandOutlined />
            算子化原因
          </Space>
        </Divider>

        <Paragraph style={{ marginBottom: 0, color: '#52607a' }}>
          当前算子具备稳定的输入输出契约，可以独立运行，并与上下游任务解耦。
          这让它既能被预置链路复用，也能被后续 agent 作为可发现、可编排的能力节点调用。
        </Paragraph>

        {operator.decoupling_reason ? (
          <>
            <Divider style={{ margin: '4px 0' }}>为什么适合做成算子</Divider>
            <Paragraph style={{ marginBottom: 0, color: '#52607a' }}>{operator.decoupling_reason}</Paragraph>
          </>
        ) : null}
      </Space>
    </Card>
  )
}

export default OperatorDetailPanel
