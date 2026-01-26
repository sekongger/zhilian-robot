import React, { useState } from 'react'
import {
  Card, Input, Button, message, Spin, Tag, Space, Row, Col, Typography, Divider
} from 'antd'
import {
  ThunderboltOutlined,
  SaveOutlined,
  ClearOutlined,
  BulbOutlined
} from '@ant-design/icons'
import { nlpService, graphService } from '../services/api'

const { TextArea } = Input
const { Title, Text } = Typography

const AnalysisPage = () => {
  const [loading, setLoading] = useState(false)
  const [text, setText] = useState('')
  const [result, setResult] = useState({ entities: {}, relations: [] })

  const sampleText = `华为技术有限公司是一家领先的全球信息与通信技术解决方案供应商。该公司与台积电合作,采购先进的芯片制造服务。华为的主要产品包括智能手机、通信设备和云计算解决方案。在机器人领域,华为与ABB、库卡等公司建立合作关系,共同推进工业机器人的智能化发展。`

  const handleAnalyze = async () => {
    if (!text.trim()) return message.warning('请输入文本')
    setLoading(true)
    try {
      const data = await nlpService.analyzeTextWithLLM({ text })
      setResult({
        entities: data.entities || {},
        relations: data.relations || []
      })
      message.success('分析完成')
    } catch (error) {
      message.error('分析失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const res = await graphService.saveToGraph(result.entities, result.relations)
      if (res.success) message.success(`已保存: ${res.entities_count} 实体, ${res.relations_count} 关系`)
      else message.error('保存失败: ' + res.error)
    } catch (error) {
      message.error('错误: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // 实体颜色映射
  const getEntityColor = (type) => {
    const colors = { companies: '#3b82f6', products: '#22c55e', technologies: '#eab308', persons: '#ef4444', locations: '#06b6d4' }
    return colors[type] || 'default'
  }

  return (
    <Row gutter={24} style={{ height: 'calc(100vh - 120px)' }}>
      {/* 左侧：输入区 */}
      <Col xs={24} lg={10} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Card
          title={<Space><ThunderboltOutlined style={{ color: '#6366f1' }} /> <span style={{ color: '#f1f5f9' }}>文本输入</span></Space>}
          style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            border: '1px solid #334155',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
          }}
          bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
          extra={
            <Button
              type="link"
              size="small"
              onClick={() => setText(sampleText)}
              style={{ color: '#6366f1' }}
            >
              加载示例
            </Button>
          }
        >
          <TextArea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="在此粘贴行业新闻、研报摘要或公司公告..."
            style={{
              flex: 1,
              resize: 'none',
              marginBottom: 20,
              padding: 14,
              fontSize: 15,
              background: '#0f172a',
              border: '1px solid #334155',
              color: '#e2e8f0',
              borderRadius: 8
            }}
          />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button
              icon={<ClearOutlined />}
              onClick={() => { setText(''); setResult({ entities: {}, relations: [] }) }}
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                color: '#94a3b8'
              }}
            >
              清空
            </Button>
            <Button
              type="primary"
              icon={<BulbOutlined />}
              loading={loading}
              onClick={handleAnalyze}
              style={{ background: '#6366f1', border: 'none' }}
            >
              智能分析
            </Button>
          </Space>
        </Card>
      </Col>

      {/* 右侧：结果区 */}
      <Col xs={24} lg={14} style={{ height: '100%', overflowY: 'auto' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 实体卡片 */}
          <Card
            title={<span style={{ color: '#f1f5f9' }}>识别实体 (NER)</span>}
            className={loading ? 'loading-blur' : ''}
            style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            {Object.keys(result.entities).length === 0 ? (
              <div style={{ textAlign: 'center', color: '#64748b', padding: '30px 0' }}>
                <BulbOutlined style={{ fontSize: 40, marginBottom: 12, opacity: 0.5 }} />
                <div>等待分析...</div>
              </div>
            ) : (
              Object.entries(result.entities).map(([type, items]) => items.length > 0 && (
                <div key={type} style={{ marginBottom: 20 }}>
                  <Text
                    style={{
                      display: 'block',
                      marginBottom: 10,
                      fontSize: 12,
                      textTransform: 'uppercase',
                      color: '#94a3b8',
                      fontWeight: 600,
                      letterSpacing: '0.05em'
                    }}
                  >
                    {type}
                  </Text>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                    {items.map((item, i) => (
                      <Tag
                        key={i}
                        color={getEntityColor(type)}
                        style={{
                          fontSize: 14,
                          padding: '6px 14px',
                          borderRadius: 6,
                          fontWeight: 500
                        }}
                      >
                        {item}
                      </Tag>
                    ))}
                  </div>
                </div>
              ))
            )}
          </Card>

          {/* 关系卡片 */}
          <Card
            title={<span style={{ color: '#f1f5f9' }}>关系链 (Relation Extraction)</span>}
            style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
            extra={
              <Button
                type="primary"
                ghost
                size="small"
                icon={<SaveOutlined />}
                disabled={result.relations.length === 0}
                onClick={handleSave}
                style={{
                  borderColor: '#6366f1',
                  color: result.relations.length === 0 ? '#64748b' : '#6366f1'
                }}
              >
                保存到图谱
              </Button>
            }
          >
            {result.relations.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#64748b', padding: '30px 0' }}>
                <SaveOutlined style={{ fontSize: 40, marginBottom: 12, opacity: 0.5 }} />
                <div>无关系数据</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {result.relations.map((rel, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: '#0f172a',
                    padding: '16px 18px',
                    borderRadius: 10,
                    border: '1px solid #334155',
                    transition: 'all 0.3s ease'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                      <Text strong style={{ color: '#f1f5f9', fontSize: 15 }}>{rel.subject}</Text>
                      <div style={{ position: 'relative', padding: '0 16px', minWidth: 60 }}>
                        <div style={{ height: 2, width: 50, background: '#475569', borderRadius: 1 }}></div>
                        <Text style={{
                          position: 'absolute',
                          top: -12,
                          left: '50%',
                          transform: 'translateX(-50%)',
                          fontSize: 12,
                          color: '#6366f1',
                          background: '#0f172a',
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontWeight: 600,
                          whiteSpace: 'nowrap'
                        }}>
                          {rel.relation}
                        </Text>
                      </div>
                      <Text strong style={{ color: '#f1f5f9', fontSize: 15 }}>{rel.object}</Text>
                    </div>
                    <Tag
                      color="gold"
                      style={{
                        marginLeft: 16,
                        fontSize: 13,
                        padding: '4px 12px',
                        borderRadius: 6,
                        fontWeight: 600
                      }}
                    >
                      {(rel.confidence * 100).toFixed(0)}%
                    </Tag>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Space>
      </Col>
    </Row>
  )
}

export default AnalysisPage