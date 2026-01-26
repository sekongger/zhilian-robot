import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Select, message, Space, Spin, Empty, Tag, Row, Col } from 'antd'
import { SearchOutlined, InfoCircleOutlined } from '@ant-design/icons'
import D3ForceGraph from '../components/D3ForceGraph'
import DashboardStats from '../components/DashboardStats'
import { graphService } from '../services/api'

const GraphPage = () => {
  const [loading, setLoading] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [depth, setDepth] = useState(2)
  const [searchText, setSearchText] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)

  // 自动搜索：检测URL参数并执行搜索
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const entityName = urlParams.get('name')
    const entityId = urlParams.get('entity')
    
    if (entityName) {
      // 设置搜索框文本
      setSearchText(entityName)
      // 自动执行搜索
      setTimeout(() => {
        handleSearch(entityName)
      }, 300)
      
      // 清除URL参数，避免刷新时重复搜索
      window.history.replaceState({}, '', '/graph')
    }
  }, [])

  const handleSearch = async (value) => {
    const term = value || searchText
    if (!term.trim()) {
      message.warning('请输入企业名称')
      return
    }
    setSearchText(term)
    setLoading(true)
    try {
      const data = await graphService.getCompanyRelations(term, depth)
      setGraphData(data)
      
      if (data.nodes.length === 0) {
        message.info('未找到相关数据')
      } else {
        message.success(`加载成功: ${data.nodes.length} 节点, ${data.edges.length} 关系`)
      }
    } catch (error) {
      message.error('查询失败: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleNodeClick = (node) => {
    setSelectedNode(node)
  }

  return (
    <div className="graph-page-container">
      {/* 搜索控制面板 */}
      <Card 
        className="search-panel-card"
        bodyStyle={{ padding: '20px' }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <SearchOutlined style={{ color: '#6366f1', fontSize: '18px' }}/> 
                <span style={{ fontSize: '16px', fontWeight: 600, color: '#e2e8f0' }}>产业链图谱探索</span>
              </div>
              <Space.Compact style={{ width: '100%' }}>
                <Select
                  value={depth}
                  onChange={setDepth}
                  style={{ width: 120 }}
                  options={[
                    { value: 1, label: '1层关系' },
                    { value: 2, label: '2层关系' },
                    { value: 3, label: '3层关系' },
                    { value: 4, label: '4层关系' },
                  ]}
                />
                <Input.Search
                  placeholder="输入企业名称，如：华为、特斯拉"
                  allowClear
                  enterButton="探索"
                  size="large"
                  onSearch={handleSearch}
                  loading={loading}
                  value={searchText}
                  onChange={e => setSearchText(e.target.value)}
                  style={{ flex: 1 }}
                />
              </Space.Compact>
            </Space>
          </Col>
          <Col>
            <Space wrap>
              <Tag color="blue" style={{ cursor: 'pointer', fontSize: '14px', padding: '4px 12px' }} onClick={() => handleSearch('华为')}>#华为</Tag>
              <Tag color="cyan" style={{ cursor: 'pointer', fontSize: '14px', padding: '4px 12px' }} onClick={() => handleSearch('特斯拉')}>#特斯拉</Tag>
              <Tag color="purple" style={{ cursor: 'pointer', fontSize: '14px', padding: '4px 12px' }} onClick={() => handleSearch('小米')}>#小米</Tag>
              <Tag color="green" style={{ cursor: 'pointer', fontSize: '14px', padding: '4px 12px' }} onClick={() => handleSearch('ABB')}>#ABB</Tag>
            </Space>
          </Col>
        </Row>
        
        {graphData.nodes.length > 0 && (
          <div style={{ 
            marginTop: '16px',
            padding: '12px', 
            background: 'rgba(99, 102, 241, 0.05)', 
            borderRadius: '8px', 
            fontSize: '13px', 
            color: '#94a3b8',
            border: '1px solid rgba(99, 102, 241, 0.2)'
          }}>
            <InfoCircleOutlined /> 当前视图包含 {graphData.nodes.length} 个实体和 {graphData.edges.length} 条关系
          </div>
        )}
      </Card>

      {/* 内容区域 */}
      {loading ? (
        <div style={{ 
          height: '500px', 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
          borderRadius: '12px',
          border: '1px solid #334155',
          marginTop: '24px'
        }}>
          <Spin size="large" tip="图谱构建中..." />
        </div>
      ) : graphData.nodes.length > 0 ? (
        <div style={{ marginTop: '24px' }}>
          {/* 统计卡片 */}
          <DashboardStats data={graphData} />
          
          {/* 图谱和详情面板 */}
          <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
            <Col xs={24} lg={selectedNode ? 18 : 24}>
              <D3ForceGraph data={graphData} onNodeClick={handleNodeClick} />
            </Col>
            
            {selectedNode && (
              <Col xs={24} lg={6}>
                <Card 
                  className="entity-detail-card"
                  title="实体详情"
                  extra={
                    <Button type="link" size="small" onClick={() => setSelectedNode(null)}>
                      关闭
                    </Button>
                  }
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="middle">
                    <div>
                      <Tag color="blue" style={{ marginBottom: '8px' }}>
                        {selectedNode.type}
                      </Tag>
                      <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: '#e2e8f0', margin: '8px 0' }}>
                        {selectedNode.name}
                      </h2>
                      <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: '1.6' }}>
                        {selectedNode.description || "暂无描述信息"}
                      </p>
                    </div>
                    
                    <div className="connections-box">
                      <p style={{ fontSize: '12px', color: '#64748b', fontWeight: 'bold', marginBottom: '12px', textTransform: 'uppercase' }}>
                        关联关系
                      </p>
                      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        {(() => {
                          // 去重：使用 Set 存储唯一的连接标识
                          const uniqueConnections = new Map();
                          graphData.edges
                            .filter(l => l.source === selectedNode.id || l.target === selectedNode.id)
                            .forEach(l => {
                              const isSource = l.source === selectedNode.id;
                              const otherNodeId = isSource ? l.target : l.source;
                              const relation = l.relation || l.relationship;
                              // 使用组合键去重：节点+关系+方向
                              const key = `${otherNodeId}-${relation}-${isSource ? 'out' : 'in'}`;
                              if (!uniqueConnections.has(key)) {
                                uniqueConnections.set(key, { l, isSource, otherNodeId });
                              }
                            });
                          
                          return Array.from(uniqueConnections.values()).map(({ l, isSource, otherNodeId }) => {
                            const otherNode = graphData.nodes.find(n => n.id === otherNodeId);
                            const relation = l.relation || l.relationship;
                            const uniqueKey = `${otherNodeId}-${relation}-${isSource ? 'out' : 'in'}`;
                            
                            return (
                              <div key={uniqueKey} style={{ 
                                padding: '8px 12px',
                                background: '#1e293b',
                                borderRadius: '6px',
                                marginBottom: '8px',
                                fontSize: '12px',
                                border: '1px solid #334155'
                              }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                                  <span style={{ color: '#3b82f6' }}>{isSource ? '→' : '←'}</span>
                                  <span style={{ color: '#6366f1', fontWeight: 500 }}>{relation}</span>
                                </div>
                                <div style={{ color: '#94a3b8', paddingLeft: '18px' }}>
                                  {otherNode?.name || otherNodeId}
                                </div>
                              </div>
                            )
                          });
                        })()}
                        {graphData.edges.filter(l => l.source === selectedNode.id || l.target === selectedNode.id).length === 0 && (
                          <p style={{ color: '#64748b', fontSize: '12px', fontStyle: 'italic' }}>暂无关联关系</p>
                        )}
                      </div>
                    </div>
                  </Space>
                </Card>
              </Col>
            )}
          </Row>
        </div>
      ) : (
        <div style={{ 
          height: '500px', 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center',
          background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
          borderRadius: '12px',
          border: '1px solid #334155',
          marginTop: '24px'
        }}>
          <Empty 
            description="请输入企业名称开始探索" 
            style={{ color: '#64748b' }}
          />
        </div>
      )}

      <style jsx>{`
        .graph-page-container {
          padding: 24px;
        }
        .search-panel-card {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
          border-radius: 12px;
        }
        .search-panel-card :global(.ant-card-body) {
          padding: 20px;
        }
        .entity-detail-card {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
          border-radius: 12px;
          height: 100%;
        }
        .entity-detail-card :global(.ant-card-head) {
          border-bottom: 1px solid #334155;
          color: #e2e8f0;
        }
        .entity-detail-card :global(.ant-card-head-title) {
          color: #e2e8f0;
          font-weight: 600;
        }
        .connections-box {
          background: rgba(15, 23, 42, 0.5);
          padding: 16px;
          border-radius: 8px;
          border: 1px solid #334155;
        }
      `}</style>
    </div>
  )
}

export default GraphPage