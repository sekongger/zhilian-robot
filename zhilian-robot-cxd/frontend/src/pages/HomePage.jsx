import React, { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Typography, Button, Skeleton } from 'antd'
import { 
  DeploymentUnitOutlined, 
  ThunderboltOutlined,
  DatabaseOutlined,
  ArrowRightOutlined,
  RiseOutlined,
  FireOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { graphService, dataService } from '../services/api'

const { Title, Paragraph, Text } = Typography

const HomePage = () => {
  const navigate = useNavigate()
  const [graphStats, setGraphStats] = useState({ node_count: 0, relation_count: 0 })
  const [dataStats, setDataStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 尝试从sessionStorage获取缓存数据
        const cachedGraphStats = sessionStorage.getItem('graphStats')
        const cachedDataStats = sessionStorage.getItem('dataStats')
        const cacheTime = sessionStorage.getItem('statsTimestamp')
        
        // 如果缓存存在且未过期（3分钟内）
        const now = Date.now()
        if (cachedGraphStats && cachedDataStats && cacheTime && (now - parseInt(cacheTime)) < 180000) {
          setGraphStats(JSON.parse(cachedGraphStats))
          setDataStats(JSON.parse(cachedDataStats))
          setLoading(false)
          return
        }
        
        // 缓存不存在或已过期，从服务器获取
        const [gStats, dStats] = await Promise.all([
          graphService.getStatistics(),
          dataService.getDataStatistics()
        ])
        setGraphStats(gStats)
        setDataStats(dStats)
        
        // 存入sessionStorage
        sessionStorage.setItem('graphStats', JSON.stringify(gStats))
        sessionStorage.setItem('dataStats', JSON.stringify(dStats))
        sessionStorage.setItem('statsTimestamp', now.toString())
      } catch (error) {
        console.error('Failed to load stats', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  // 功能卡片组件
  const FeatureCard = ({ icon, title, desc, link, color, bg }) => (
    <Card 
      hoverable 
      style={{ 
        height: '100%', 
        borderTop: `3px solid ${color}`,
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        border: '1px solid #334155',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)',
        transition: 'all 0.3s ease'
      }}
      bodyStyle={{ padding: '24px' }}
      onClick={() => navigate(link)}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
        <div style={{ 
          padding: '14px', 
          borderRadius: '12px', 
          background: `${color}20`, 
          color: color,
          fontSize: '28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: `1px solid ${color}40`
        }}>
          {icon}
        </div>
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: '0 0 8px 0', color: '#f1f5f9' }}>
            {title}
          </Title>
          <Paragraph style={{ 
            marginBottom: '16px', 
            minHeight: '60px', 
            color: '#94a3b8',
            fontSize: '14px',
            lineHeight: '1.6'
          }}>
            {desc}
          </Paragraph>
          <Button 
            type="link" 
            style={{ 
              padding: 0, 
              color: color,
              fontWeight: 600 
            }} 
            icon={<ArrowRightOutlined />}
          >
            立即开始
          </Button>
        </div>
      </div>
    </Card>
  )

  return (
    <div>
      {/* Hero Section */}
      <Card 
        style={{ 
          marginBottom: 32, 
          background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #a855f7 100%)', 
          color: 'white',
          border: 'none',
          overflow: 'hidden',
          position: 'relative',
          boxShadow: '0 10px 30px rgba(99, 102, 241, 0.3)'
        }}
        bodyStyle={{ padding: '48px', position: 'relative', zIndex: 1 }}
      >
        {/* 装饰性背景圆 */}
        <div style={{
          position: 'absolute', top: -50, right: -50, width: 300, height: 300,
          background: 'rgba(255,255,255,0.08)', borderRadius: '50%', filter: 'blur(40px)'
        }} />
        <div style={{
          position: 'absolute', bottom: -80, right: 150, width: 200, height: 200,
          background: 'rgba(255,255,255,0.05)', borderRadius: '50%', filter: 'blur(30px)'
        }} />

        <Row align="middle">
          <Col xs={24} md={16}>
            <Title style={{ color: 'white', fontSize: '42px', marginBottom: '20px', fontWeight: 700 }}>
              探索机器人产业的无限连接
            </Title>
            <Paragraph style={{ 
              color: 'rgba(255,255,255,0.95)', 
              fontSize: '18px', 
              maxWidth: '650px',
              lineHeight: '1.8',
              marginBottom: '36px'
            }}>
              基于 DeepSeek 大模型驱动，自动构建产业链知识图谱。从海量文本中发现价值，辅助产业决策。
            </Paragraph>
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
              <Button 
                size="large" 
                style={{ 
                  height: '44px',
                  background: 'white',
                  color: '#4f46e5',
                  border: 'none',
                  fontWeight: 600,
                  paddingLeft: '32px',
                  paddingRight: '32px'
                }}
                onClick={() => navigate('/graph')}
              >
                开始图谱探索
              </Button>
              <Button 
                size="large" 
                style={{ 
                  height: '44px',
                  border: '2px solid rgba(255,255,255,0.4)', 
                  background: 'rgba(255,255,255,0.1)', 
                  color: 'white',
                  fontWeight: 600,
                  backdropFilter: 'blur(10px)',
                  paddingLeft: '32px',
                  paddingRight: '32px'
                }} 
                onClick={() => navigate('/analysis')}
              >
                文本智能分析
              </Button>
              <Button 
                size="large" 
                style={{ 
                  height: '44px',
                  border: '2px solid rgba(236, 72, 153, 0.6)',  // 使用粉色边框区分
                  background: 'rgba(236, 72, 153, 0.2)',      // 轻微粉色半透明背景
                  color: 'white',
                  fontWeight: 600,
                  backdropFilter: 'blur(10px)',
                  paddingLeft: '32px',
                  paddingRight: '32px'
                }} 
                onClick={() => navigate('/data')}
              >
                进入数据中心
              </Button>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 统计数据区域 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={8}>
          <Card 
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            <Skeleton loading={loading} active paragraph={{ rows: 1 }}>
              <Statistic
                title={<Text style={{ color: '#94a3b8', fontSize: '14px' }}>图谱实体节点</Text>}
                value={graphStats.node_count}
                prefix={<DeploymentUnitOutlined style={{ color: '#6366f1', fontSize: '20px' }} />}
                suffix="个"
                valueStyle={{ fontWeight: 700, color: '#f1f5f9', fontSize: '32px' }}
              />
            </Skeleton>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card 
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            <Skeleton loading={loading} active paragraph={{ rows: 1 }}>
              <Statistic
                title={<Text style={{ color: '#94a3b8', fontSize: '14px' }}>产业链关系</Text>}
                value={graphStats.relation_count}
                prefix={<RiseOutlined style={{ color: '#22c55e', fontSize: '20px' }} />}
                suffix="条"
                valueStyle={{ fontWeight: 700, color: '#f1f5f9', fontSize: '32px' }}
              />
            </Skeleton>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card 
            bordered={false}
            style={{
              background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
              border: '1px solid #334155',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
          >
            <Skeleton loading={loading} active paragraph={{ rows: 1 }}>
              <Statistic
                title={<Text style={{ color: '#94a3b8', fontSize: '14px' }}>知识库文章</Text>}
                value={dataStats?.total_articles || 0}
                prefix={<DatabaseOutlined style={{ color: '#f59e0b', fontSize: '20px' }} />}
                suffix="篇"
                valueStyle={{ fontWeight: 700, color: '#f1f5f9', fontSize: '32px' }}
              />
            </Skeleton>
          </Card>
        </Col>
      </Row>

      {/* 功能导航区域 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} sm={12} lg={6}>
          <FeatureCard 
            title="图谱探索" 
            desc="可视化查询企业上下游关系，支持多层级穿透分析，发现潜在商业机会。"
            icon={<DeploymentUnitOutlined />}
            link="/graph"
            color="#6366f1"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <FeatureCard 
            title="时序分析" 
            desc="追踪实体动量变化趋势，识别热点话题，监控特别关注对象的时间演化。"
            icon={<FireOutlined />}
            link="/temporal"
            color="#ef4444"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <FeatureCard 
            title="智能分析" 
            desc="上传行业报告或新闻，利用 LLM 自动提取实体与关系，一键存入知识库。"
            icon={<ThunderboltOutlined />}
            link="/analysis"
            color="#a855f7"
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <FeatureCard 
            title="数据中心" 
            desc="管理 RSS 订阅源与爬虫任务，监控数据采集状态，进行数据清洗与维护。"
            icon={<DatabaseOutlined />}
            link="/data"
            color="#ec4899"
          />
        </Col>
      </Row>
    </div>
  )
}

export default HomePage