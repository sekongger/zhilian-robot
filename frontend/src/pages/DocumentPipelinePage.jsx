import React, { useEffect, useState } from 'react'
import { Card, Tabs, Tag, Button, Space, message, Statistic, Row, Col, Segmented, Tooltip } from 'antd'
import { 
  FileTextOutlined, 
  FilePdfOutlined, 
  AuditOutlined, 
  BankOutlined, 
  ExperimentOutlined, 
  ShoppingOutlined, 
  SyncOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'
import { documentPipelineService } from '../services/documentPipelineApi'

// 子组件导入
import DataResourceLayer from '../components/document/DataResourceLayer'
import DataElementLayer from '../components/document/DataElementLayer'
import DataServiceLayer from '../components/document/DataServiceLayer'

const DocumentPipelinePage = () => {
  const [activeTab, setActiveTab] = useState('resource')
  const [docType, setDocType] = useState('news')
  const [stats, setStats] = useState(null)
  const [overallStats, setOverallStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [knowledgeScope, setKnowledgeScope] = useState('selected')

  // 文档类型配置
  const docTypeConfig = {
    news: {
      key: 'news',
      name: '资讯',
      nameEn: 'News',
      icon: <FileTextOutlined />,
      color: '#52c41a',
      status: 'supported',
      description: '新闻、快讯、公告等时效性信息',
    },
    report: {
      key: 'report',
      name: '研报',
      nameEn: 'Report',
      icon: <FilePdfOutlined />,
      color: '#1890ff',
      status: 'supported',
      description: '研究报告、行业分析报告',
    },
    policy: {
      key: 'policy',
      name: '政策',
      nameEn: 'Policy',
      icon: <AuditOutlined />,
      color: '#faad14',
      status: 'planned',
      description: '政府政策文件、法规',
    },
    patent: {
      key: 'patent',
      name: '专利',
      nameEn: 'Patent',
      icon: <ExperimentOutlined />,
      color: '#722ed1',
      status: 'planned',
      description: '专利文献',
    },
    company: {
      key: 'company',
      name: '企业',
      nameEn: 'Company',
      icon: <BankOutlined />,
      color: '#13c2c2',
      status: 'planned',
      description: '工商信息、企业画像',
    },
    product: {
      key: 'product',
      name: '产品',
      nameEn: 'Product',
      icon: <ShoppingOutlined />,
      color: '#eb2f96',
      status: 'planned',
      description: '产品信息、规格参数',
    },
  }

  const fetchStats = async (targetDocType = docType, scope = knowledgeScope) => {
    const resolvedDocType = typeof targetDocType === 'string' ? targetDocType : docType
    setLoading(true)
    try {
      const [overallRes, typedRes] = await Promise.all([
        documentPipelineService.getStats(),
        documentPipelineService.getStats({ doc_type: resolvedDocType, knowledge_scope: scope }),
      ])
      setOverallStats(overallRes)
      setStats(typedRes)
    } catch (err) {
      message.error(err.message || '获取数据统计失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats(docType, knowledgeScope)
  }, [docType, knowledgeScope])

  // 文档类型选项（用于顶部 Segmented）
  const docTypeOptions = Object.values(docTypeConfig).map(item => ({
    label: (
      <Tooltip title={item.description}>
        <Space>
          {item.icon}
          <span>{item.name}</span>
          {item.status === 'supported' ? (
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          ) : (
            <ClockCircleOutlined style={{ color: '#999', fontSize: 12 }} />
          )}
        </Space>
      </Tooltip>
    ),
    value: item.key,
    disabled: item.status !== 'supported',
  }))

  // Tab 配置（仅三层）
  const tabItems = [
    {
      key: 'resource',
      label: (
        <Space>
          <DatabaseOutlined />
          数据资源层
        </Space>
      ),
      children: (
        <DataResourceLayer
          docType={docType}
          docTypeConfig={docTypeConfig}
          stats={stats}
          onRefresh={fetchStats}
        />
      ),
    },
    {
      key: 'element',
      label: (
        <Space>
          <AppstoreOutlined />
          数据要素层
        </Space>
      ),
      children: (
        <DataElementLayer
          docType={docType}
          docTypeConfig={docTypeConfig}
          stats={stats}
          onRefresh={fetchStats}
          knowledgeScope={knowledgeScope}
          onKnowledgeScopeChange={setKnowledgeScope}
        />
      ),
    },
    {
      key: 'service',
      label: (
        <Space>
          <ApiOutlined />
          数据服务层
        </Space>
      ),
      children: (
        <DataServiceLayer
          docType={docType}
          docTypeConfig={docTypeConfig}
          stats={stats}
          onRefresh={fetchStats}
        />
      ),
    },
  ]

  const summaryStats = overallStats || stats

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 顶部：文档类型选择器 */}
      <Card size="small">
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="large">
              <span style={{ fontWeight: 600, fontSize: 16 }}>文档类型：</span>
              <Segmented
                value={docType}
                onChange={setDocType}
                options={docTypeOptions}
                size="large"
              />
            </Space>
          </Col>
          <Col>
            <Space size="large">
              <Statistic
                title="原始文档（全量）"
                value={summaryStats?.raw_layer?.raw_documents ?? 0}
                valueStyle={{ fontSize: 16 }}
              />
              <Statistic
                title="标准化文档（全量）"
                value={summaryStats?.resource_layer?.inc_document ?? 0}
                valueStyle={{ fontSize: 16 }}
              />
              <Statistic
                title="实体（全量）"
                value={summaryStats?.knowledge_layer?.entities ?? 0}
                valueStyle={{ fontSize: 16 }}
              />
              <Statistic
                title="陈述（全量）"
                value={summaryStats?.knowledge_layer?.statements ?? 0}
                valueStyle={{ fontSize: 16 }}
              />
              <Button icon={<SyncOutlined spin={loading} />} onClick={fetchStats} loading={loading}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 主体：三层 Tab */}
      <Card
        title={
          <Space>
            <span>文档处理中心</span>
            <Tag color={docTypeConfig[docType]?.color}>
              {docTypeConfig[docType]?.name}
            </Tag>
          </Space>
        }
        bodyStyle={{ padding: 0 }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="card"
          size="large"
          items={tabItems}
          tabBarStyle={{ marginBottom: 0, padding: '0 16px' }}
          style={{ minHeight: 600 }}
        />
      </Card>
    </div>
  )
}

export default DocumentPipelinePage
