import React, { useEffect, useMemo, useState } from 'react'
import { Button, Card, Collapse, Empty, Input, List, Space, Tag, Typography } from 'antd'
import { FilterOutlined, MinusSquareOutlined, PlusSquareOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { getCatalogOperatorBadgeRows, serializeDragPayload } from './operatorWorkbenchUtils.mjs'

const { Search } = Input
const { Text, Paragraph } = Typography

const OperatorCatalogPanel = ({
  loading = false,
  layers = [],
  operators = [],
  searchValue = '',
  onSearchChange,
  selectedOperatorName,
  onSelectOperator,
  onAddOperator,
}) => {
  const operatorsByLayer = useMemo(
    () =>
      layers
        .map((layer) => ({
          ...layer,
          operators: operators.filter(
            (operator) => (operator.knowledge_category || operator.layer) === layer.key,
          ),
        }))
        .filter((layer) => layer.operators.length > 0),
    [layers, operators],
  )

  const [expandedKeys, setExpandedKeys] = useState([])

  useEffect(() => {
    setExpandedKeys((current) => (current.length ? current.filter((key) => operatorsByLayer.some((layer) => layer.key === key)) : operatorsByLayer.map((layer) => layer.key)))
  }, [operatorsByLayer])

  return (
    <Card
      title="知识计算算子目录"
      extra={
        <Space size={8}>
          <Button
            size="small"
            icon={<PlusSquareOutlined />}
            onClick={() => setExpandedKeys(operatorsByLayer.map((layer) => layer.key))}
          >
            展开全部
          </Button>
          <Button size="small" icon={<MinusSquareOutlined />} onClick={() => setExpandedKeys([])}>
            收起全部
          </Button>
          <Tag color="blue" style={{ marginInlineEnd: 0 }}>
            {operators.length} 个算子
          </Tag>
        </Space>
      }
      styles={{ body: { padding: 16 } }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Search
          allowClear
          placeholder="搜索算子名、阶段或标签"
          value={searchValue}
          onChange={(event) => onSearchChange?.(event.target.value)}
        />

        {operatorsByLayer.length === 0 ? <Empty description="没有匹配的算子" /> : null}

        <Collapse
          ghost
          activeKey={expandedKeys}
          onChange={(keys) => setExpandedKeys(Array.isArray(keys) ? keys : [keys])}
          items={operatorsByLayer.map((layer) => ({
            key: layer.key,
            label: (
              <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                <Space direction="vertical" size={0}>
                  <Text strong style={{ color: '#14213d' }}>
                    {layer.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {layer.description}
                  </Text>
                </Space>
                <Tag color="blue">{layer.operators.length}</Tag>
              </Space>
            ),
            children: (
              <List
                loading={loading}
                dataSource={layer.operators}
                renderItem={(operator) => {
                  const selected = operator.name === selectedOperatorName
                  const { stateBadges, ioBadges } = getCatalogOperatorBadgeRows(operator)
                  return (
                    <List.Item
                      onClick={() => onSelectOperator?.(operator.name)}
                      draggable
                      onDoubleClick={() => onAddOperator?.(operator.name)}
                      onDragStart={(event) => {
                        const payload = serializeDragPayload({ source: 'catalog', operator: operator.name })
                        event.dataTransfer.effectAllowed = 'copy'
                        event.dataTransfer.setData('application/json', payload)
                        event.dataTransfer.setData('text/plain', payload)
                      }}
                      style={{
                        cursor: 'grab',
                        borderRadius: 12,
                        padding: 14,
                        marginBottom: 8,
                        border: selected ? '1px solid #1c7ed6' : '1px solid #d7e0ea',
                        background: selected ? 'rgba(28, 126, 214, 0.08)' : '#ffffff',
                        boxShadow: selected ? '0 10px 24px rgba(28, 126, 214, 0.12)' : 'none',
                      }}
                    >
                      <Space direction="vertical" size={8} style={{ width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, width: '100%' }}>
                          <ThunderboltOutlined style={{ color: '#0b6e99', marginTop: 4, flex: '0 0 auto' }} />
                          <Text
                            strong
                            style={{
                              color: '#14213d',
                              fontSize: 18,
                              lineHeight: 1.45,
                              display: 'block',
                              flex: 1,
                              minWidth: 0,
                              whiteSpace: 'normal',
                              wordBreak: 'break-word',
                              overflowWrap: 'anywhere',
                            }}
                          >
                            {operator.name}
                          </Text>
                        </div>

                        <Space wrap size={[6, 6]} style={{ width: '100%' }}>
                          {stateBadges.map((item) => (
                            <Tag key={item.key} color={item.color}>
                              {item.label}
                            </Tag>
                          ))}
                        </Space>

                        <Paragraph
                          style={{ marginBottom: 0, color: '#52607a', fontSize: 13, lineHeight: 1.7 }}
                          ellipsis={{ rows: 2 }}
                        >
                          {operator.description}
                        </Paragraph>

                        <Space wrap size={[6, 6]}>
                          {ioBadges.map((item, index) => (
                            <Tag key={item.key} icon={index === 0 ? <FilterOutlined /> : undefined} color={item.color}>
                              {item.label}
                            </Tag>
                          ))}
                        </Space>
                      </Space>
                    </List.Item>
                  )
                }}
              />
            ),
          }))}
        />
      </Space>
    </Card>
  )
}

export default OperatorCatalogPanel
