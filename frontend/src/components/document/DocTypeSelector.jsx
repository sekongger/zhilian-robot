import React from 'react'
import { Card, Row, Col, Statistic, Tag, Badge } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'

/**
 * 文档类型选择器组件
 * 展示各文档类型卡片和统计信息
 */
const DocTypeSelector = ({ docTypeConfig, selectedType, onSelect, stats }) => {
  // 根据文档类型获取统计数量
  const getDocCount = (typeKey) => {
    if (!stats) return 0
    switch (typeKey) {
      case 'news':
        return stats?.resource_layer?.source_news ?? stats?.raw_layer?.raw_documents ?? 0
      case 'report':
        return stats?.resource_layer?.source_report ?? 0
      case 'policy':
        return stats?.resource_layer?.source_policy ?? 0
      case 'patent':
        return stats?.resource_layer?.source_patent ?? 0
      case 'company':
        return stats?.resource_layer?.source_company ?? 0
      case 'product':
        return stats?.resource_layer?.source_product ?? 0
      default:
        return 0
    }
  }

  const renderStatusTag = (status) => {
    if (status === 'supported') {
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          已支持
        </Tag>
      )
    }
    return (
      <Tag icon={<ClockCircleOutlined />} color="default">
        规划中
      </Tag>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 8 }}>选择文档类型</h3>
        <p style={{ color: '#888', margin: 0 }}>
          点击选择要处理的文档类型，系统将根据类型展示对应的处理流程和数据统计
        </p>
      </div>

      <Row gutter={[16, 16]}>
        {Object.values(docTypeConfig).map((docType) => {
          const isSelected = selectedType === docType.key
          const isSupported = docType.status === 'supported'
          const count = getDocCount(docType.key)

          return (
            <Col span={8} key={docType.key}>
              <Badge.Ribbon
                text={docType.status === 'supported' ? '可用' : '规划中'}
                color={docType.status === 'supported' ? 'green' : 'gray'}
              >
                <Card
                  hoverable={isSupported}
                  onClick={() => isSupported && onSelect(docType.key)}
                  style={{
                    cursor: isSupported ? 'pointer' : 'not-allowed',
                    opacity: isSupported ? 1 : 0.6,
                    borderColor: isSelected ? docType.color : undefined,
                    borderWidth: isSelected ? 2 : 1,
                    background: isSelected ? `${docType.color}10` : undefined,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
                    <div
                      style={{
                        fontSize: 36,
                        color: docType.color,
                        opacity: isSupported ? 1 : 0.5,
                      }}
                    >
                      {docType.icon}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <span style={{ fontSize: 18, fontWeight: 600 }}>{docType.name}</span>
                        <span style={{ color: '#888', fontSize: 12 }}>{docType.nameEn}</span>
                      </div>
                      <p style={{ color: '#888', margin: '0 0 12px 0', fontSize: 13 }}>
                        {docType.description}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Statistic
                          value={count}
                          suffix="条"
                          valueStyle={{ fontSize: 20, color: docType.color }}
                        />
                        {renderStatusTag(docType.status)}
                      </div>
                    </div>
                  </div>
                </Card>
              </Badge.Ribbon>
            </Col>
          )
        })}
      </Row>

      <Card style={{ marginTop: 24 }} size="small">
        <Row gutter={24}>
          <Col span={6}>
            <Statistic
              title="已支持类型"
              value={Object.values(docTypeConfig).filter((d) => d.status === 'supported').length}
              suffix={`/ ${Object.keys(docTypeConfig).length}`}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="总文档数"
              value={stats?.raw_layer?.raw_documents ?? 0}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已标准化"
              value={stats?.resource_layer?.lnc_document ?? 0}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="已抽取实体"
              value={stats?.knowledge_layer?.entities ?? 0}
            />
          </Col>
        </Row>
      </Card>
    </div>
  )
}

export default DocTypeSelector
