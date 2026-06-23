import React, { useState } from 'react'
import { Card, Row, Col, Statistic, Button, Tag, message, Typography, Input, Space, Steps, Progress, Empty, Timeline, Descriptions, Divider, Tooltip } from 'antd'
import { SearchOutlined, ThunderboltOutlined, AuditOutlined, LineChartOutlined, BulbOutlined, SwapOutlined, ApiOutlined, DatabaseOutlined, CloudServerOutlined } from '@ant-design/icons'
import { documentPipelineService } from '../../services/documentPipelineApi'
import D3ForceGraph from '../D3ForceGraph'

const { Text, Paragraph, Title } = Typography

/**
 * 数据服务层组件
 * 展示检索服务、缓存服务和应用场景（根据文档类型动态变化）
 */
const DataServiceLayer = ({ docType, docTypeConfig, stats, onRefresh }) => {
  // 资讯场景状态
  const [collabInput, setCollabInput] = useState('上海交大')
  const [collabResult, setCollabResult] = useState(null)
  const [collabLoading, setCollabLoading] = useState(false)
  const [matchInput, setMatchInput] = useState('AI')
  const [matchResult, setMatchResult] = useState(null)
  const [matchLoading, setMatchLoading] = useState(false)
  const [provInput, setProvInput] = useState('合作')
  const [provResult, setProvResult] = useState(null)
  const [provLoading, setProvLoading] = useState(false)

  // 研报场景状态
  const [trendInput, setTrendInput] = useState('新能源')
  const [trendResult, setTrendResult] = useState(null)
  const [trendLoading, setTrendLoading] = useState(false)
  const [viewpointInput, setViewpointInput] = useState('')
  const [viewpointResult, setViewpointResult] = useState(null)
  const [viewpointLoading, setViewpointLoading] = useState(false)

  const getDocTypeLabel = (docKey) => {
    if (!docKey) return null
    return docTypeConfig[docKey]?.name || docKey
  }

  const renderDocTypeTag = (docKey, title) => {
    if (!docKey) return null
    const label = getDocTypeLabel(docKey)
    if (title && label && title.includes(label)) return null
    return (
      <Tag color={docTypeConfig[docKey]?.color}>
        {label}
      </Tag>
    )
  }

  const renderTitleWithDocType = (title, docKey) => {
    if (!docKey) return title
    return (
      <Space size={6} wrap>
        <span>{title}</span>
        {renderDocTypeTag(docKey, title)}
      </Space>
    )
  }

  // 资讯场景方法
  const runCollaboration = async () => {
    setCollabLoading(true)
    try {
      const res = await documentPipelineService.scenarioCollaboration(collabInput)
      setCollabResult(res)
    } catch (err) {
      message.error(err.message || '合作监测查询失败')
    } finally {
      setCollabLoading(false)
    }
  }

  const runTechMatch = async () => {
    setMatchLoading(true)
    try {
      const res = await documentPipelineService.scenarioTechMatch(matchInput)
      setMatchResult(res)
    } catch (err) {
      message.error(err.message || '供需匹配查询失败')
    } finally {
      setMatchLoading(false)
    }
  }

  const runProvenance = async () => {
    setProvLoading(true)
    try {
      const res = await documentPipelineService.scenarioProvenance(provInput)
      setProvResult(res)
    } catch (err) {
      message.error(err.message || '溯源审计查询失败')
    } finally {
      setProvLoading(false)
    }
  }

  // 研报场景方法（模拟）
  const runTrendAnalysis = async () => {
    setTrendLoading(true)
    try {
      // TODO: 替换为实际API
      await new Promise(resolve => setTimeout(resolve, 1500))
      setTrendResult({
        keyword: trendInput,
        total_reports: 28,
        time_range: '2025-01 ~ 2026-02',
        trends: [
          { period: '2025Q1', sentiment: 'positive', count: 8 },
          { period: '2025Q2', sentiment: 'positive', count: 12 },
          { period: '2025Q3', sentiment: 'neutral', count: 5 },
          { period: '2025Q4', sentiment: 'positive', count: 3 },
        ],
        top_institutions: ['中信证券', '国泰君安', '华泰证券'],
        key_viewpoints: [
          '新能源汽车渗透率持续提升',
          '储能行业迎来爆发期',
          '光伏产业链价格企稳',
        ],
      })
    } catch (err) {
      message.error(err.message || '趋势分析失败')
    } finally {
      setTrendLoading(false)
    }
  }

  const runViewpointExtract = async () => {
    setViewpointLoading(true)
    try {
      // TODO: 替换为实际API
      await new Promise(resolve => setTimeout(resolve, 1200))
      setViewpointResult({
        total: 15,
        viewpoints: [
          { institution: '中信证券', rating: '买入', target: '宁德时代', price: '280元', confidence: 0.92 },
          { institution: '国泰君安', rating: '增持', target: '比亚迪', price: '350元', confidence: 0.88 },
          { institution: '华泰证券', rating: '买入', target: '隆基绿能', price: '45元', confidence: 0.85 },
        ],
      })
    } catch (err) {
      message.error(err.message || '观点提取失败')
    } finally {
      setViewpointLoading(false)
    }
  }

  // 渲染资讯场景
  const renderNewsScenarios = () => (
    <Row gutter={[16, 16]}>
      <Col span={8}>
        <Card size="small" title={<><ThunderboltOutlined /> 产业合作监测</>}>
          <Paragraph type="secondary">
            基于合作事件与主体关系，形成行业协同热度与合作网络。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={collabInput} onChange={(e) => setCollabInput(e.target.value)} placeholder="输入企业名称" />
            <Button type="primary" loading={collabLoading} onClick={runCollaboration}>
              运行监测
            </Button>
            <Steps
              size="small"
              current={collabLoading ? 1 : collabResult ? 2 : 0}
              items={[
                { title: '输入企业' },
                { title: '图谱检索' },
                { title: '生成合作网络' },
              ]}
            />
            {collabResult && (
              <Card size="small">
                <Text type="secondary">关联关系: {collabResult.total}</Text>
                {collabResult.relations?.length ? (
                  <div style={{ height: 300, marginTop: 12 }}>
                    <D3ForceGraph
                      data={{
                        nodes: Array.from(
                          new Set(
                            collabResult.relations
                              .flatMap((r) => [r.source, r.target])
                              .filter(Boolean)
                          )
                        ).map((name) => ({
                          id: name,
                          name,
                          type: 'companies',
                        })),
                        edges: collabResult.relations.map((r, idx) => ({
                          id: `${r.source}-${r.target}-${idx}`,
                          source: r.source,
                          target: r.target,
                          label: r.relation || 'RELATION',
                        })),
                      }}
                    />
                  </div>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关系数据" />
                )}
              </Card>
            )}
          </Space>
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={<><SwapOutlined /> 技术供需匹配</>}>
          <Paragraph type="secondary">
            利用要素实体 + 图谱关系，自动匹配技术供给与需求主体。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={matchInput} onChange={(e) => setMatchInput(e.target.value)} placeholder="输入技术关键词" />
            <Button type="primary" loading={matchLoading} onClick={runTechMatch}>
              开始匹配
            </Button>
            <Progress percent={matchLoading ? 60 : matchResult ? 100 : 0} size="small" />
            {matchResult && (
              <Card size="small">
                <Text type="secondary">匹配要素: {matchResult.matched_elements?.length || 0}</Text>
                {matchResult.matched_elements?.length ? (
                  <Descriptions size="small" column={1} bordered style={{ marginTop: 8 }}>
                    {matchResult.matched_elements.slice(0, 5).map((item) => (
                      <Descriptions.Item key={item.id} label={`${item.type} | 评分 ${item.score}`}>
                        {item.name}（引用 {item.ref_count || 0}）
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无匹配要素" />
                )}
              </Card>
            )}
          </Space>
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={<><AuditOutlined /> 资讯溯源审计</>}>
          <Paragraph type="secondary">
            通过陈述上下文字段溯源链路，支持证据核验与可信评估。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={provInput} onChange={(e) => setProvInput(e.target.value)} placeholder="输入资讯标题关键词" />
            <Button type="primary" loading={provLoading} onClick={runProvenance}>
              开始审计
            </Button>
            <Steps
              size="small"
              current={provLoading ? 1 : provResult ? 2 : 0}
              items={[
                { title: '定位资讯' },
                { title: '读取上下文' },
                { title: '生成溯源链路' },
              ]}
            />
            {provResult && (
              <Card size="small">
                <Text type="secondary">{provResult.matched ? provResult.title : '未找到资讯'}</Text>
                {provResult.provenance?.length ? (
                  <Timeline style={{ marginTop: 8 }}>
                    {provResult.provenance.map((item, idx) => (
                      <Timeline.Item key={idx} color={item.audit_status === 'approved' ? 'green' : 'gray'}>
                        <Paragraph style={{ marginBottom: 0 }}>来源: {item.source_name || '--'}</Paragraph>
                        <Paragraph style={{ marginBottom: 0 }} type="secondary">置信度: {item.confidence ?? '--'}</Paragraph>
                      </Timeline.Item>
                    ))}
                  </Timeline>
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无溯源记录" />
                )}
              </Card>
            )}
          </Space>
        </Card>
      </Col>
    </Row>
  )

  // 渲染研报场景
  const renderReportScenarios = () => (
    <Row gutter={[16, 16]}>
      <Col span={8}>
        <Card size="small" title={<><LineChartOutlined /> 行业趋势分析</>}>
          <Paragraph type="secondary">
            聚合多篇研报观点，分析行业发展趋势和市场情绪变化。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={trendInput} onChange={(e) => setTrendInput(e.target.value)} placeholder="输入行业关键词" />
            <Button type="primary" loading={trendLoading} onClick={runTrendAnalysis}>
              分析趋势
            </Button>
            <Progress percent={trendLoading ? 50 : trendResult ? 100 : 0} size="small" />
            {trendResult && (
              <Card size="small">
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="相关研报">{trendResult.total_reports} 篇</Descriptions.Item>
                  <Descriptions.Item label="时间范围">{trendResult.time_range}</Descriptions.Item>
                  <Descriptions.Item label="主要机构">
                    {trendResult.top_institutions?.map((inst, i) => (
                      <Tag key={i} color="blue">{inst}</Tag>
                    ))}
                  </Descriptions.Item>
                </Descriptions>
                <Divider style={{ margin: '12px 0' }} />
                <Text strong>核心观点：</Text>
                <ul style={{ paddingLeft: 20, marginTop: 8 }}>
                  {trendResult.key_viewpoints?.map((vp, i) => (
                    <li key={i}><Text type="secondary">{vp}</Text></li>
                  ))}
                </ul>
              </Card>
            )}
          </Space>
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={<><BulbOutlined /> 投资观点提取</>}>
          <Paragraph type="secondary">
            提取研报中的投资建议、目标价和评级信息。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input value={viewpointInput} onChange={(e) => setViewpointInput(e.target.value)} placeholder="输入股票/行业名称（可选）" />
            <Button type="primary" loading={viewpointLoading} onClick={runViewpointExtract}>
              提取观点
            </Button>
            <Steps
              size="small"
              current={viewpointLoading ? 1 : viewpointResult ? 2 : 0}
              items={[
                { title: '检索研报' },
                { title: '观点抽取' },
                { title: '汇总展示' },
              ]}
            />
            {viewpointResult && (
              <Card size="small">
                <Text type="secondary">提取观点: {viewpointResult.total} 条</Text>
                <Descriptions size="small" column={1} bordered style={{ marginTop: 8 }}>
                  {viewpointResult.viewpoints?.map((vp, idx) => (
                    <Descriptions.Item
                      key={idx}
                      label={
                        <Space>
                          <Text>{vp.institution}</Text>
                          <Tag color={vp.rating === '买入' ? 'red' : vp.rating === '增持' ? 'orange' : 'default'}>
                            {vp.rating}
                          </Tag>
                        </Space>
                      }
                    >
                      {vp.target} | 目标价 {vp.price} | 置信度 {(vp.confidence * 100).toFixed(0)}%
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            )}
          </Space>
        </Card>
      </Col>
      <Col span={8}>
        <Card size="small" title={<><SwapOutlined /> 研报对比分析</>}>
          <Paragraph type="secondary">
            对比不同机构对同一标的的研究观点和预测差异。
          </Paragraph>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input placeholder="输入股票代码或名称" />
            <Button type="primary" disabled>
              对比分析（开发中）
            </Button>
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="功能开发中，敬请期待" />
          </Space>
        </Card>
      </Col>
    </Row>
  )

  // 渲染规划中类型的场景
  const renderPlannedScenarios = () => (
    <Card>
      <div style={{ textAlign: 'center', padding: 60 }}>
        <div style={{ fontSize: 48, marginBottom: 16, color: '#888' }}>
          {docTypeConfig[docType]?.icon}
        </div>
        <h3>{docTypeConfig[docType]?.name}应用场景</h3>
        <p style={{ color: '#888' }}>该文档类型的应用场景正在规划中，敬请期待...</p>
      </div>
    </Card>
  )

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <ApiOutlined style={{ marginRight: 8 }} />
          数据服务层
          <Tag color={docTypeConfig[docType]?.color} style={{ marginLeft: 12 }}>
            {docTypeConfig[docType]?.name}
          </Tag>
        </Title>
        <Text type="secondary">
          提供检索服务、缓存服务、API网关和应用场景编排。ES统一索引实体/陈述/文档，Redis缓存高频查询。
        </Text>
      </div>

      {/* 检索与缓存服务 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title={<><SearchOutlined /> 检索服务（Elasticsearch）</>} size="small">
            <Row gutter={16}>
              <Col span={4}>
                <Card size="small">
                  <Statistic title={renderTitleWithDocType('文档索引', docType)} value={stats?.service_layer?.indices ?? 0} prefix={<DatabaseOutlined />} />
                  <Text type="secondary" style={{ fontSize: 12 }}>document_index</Text>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title={renderTitleWithDocType('实体索引', docType)} value={stats?.service_layer?.entity_indices ?? 0} prefix={<DatabaseOutlined />} />
                  <Text type="secondary" style={{ fontSize: 12 }}>entity_index</Text>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title={renderTitleWithDocType('陈述索引', docType)} value={stats?.service_layer?.statement_indices ?? 0} prefix={<DatabaseOutlined />} />
                  <Text type="secondary" style={{ fontSize: 12 }}>statement_index</Text>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="缓存键(Redis)" value={stats?.service_layer?.cache ?? 0} prefix={<CloudServerOutlined />} />
                  <Text type="secondary" style={{ fontSize: 12 }}>高频查询缓存</Text>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="API调用/日" value={stats?.service_layer?.api_calls ?? '--'} prefix={<ApiOutlined />} />
                  <Text type="secondary" style={{ fontSize: 12 }}>API Gateway</Text>
                </Card>
              </Col>
              <Col span={4}>
                <Card size="small">
                  <Statistic title="平均响应" value={stats?.service_layer?.avg_latency ?? '--'} suffix="ms" />
                  <Text type="secondary" style={{ fontSize: 12 }}>查询延迟</Text>
                </Card>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 应用场景 */}
        <Col span={24}>
          <Card 
            title={
              <Space>
                <ThunderboltOutlined />
                应用场景
                <Tag color={docTypeConfig[docType]?.color}>{docTypeConfig[docType]?.name}</Tag>
              </Space>
            } 
            size="small"
          >
            {docType === 'news' && renderNewsScenarios()}
            {docType === 'report' && renderReportScenarios()}
            {docTypeConfig[docType]?.status === 'planned' && renderPlannedScenarios()}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DataServiceLayer
