import React, { useMemo } from 'react'
import { App as AntdApp, Button, Card, Col, Divider, Row, Space, Tag, Typography } from 'antd'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRightOutlined } from '@ant-design/icons'
import { getPlatformTabByKey, resolvePlatformTabKey } from './platformTabs.mjs'
import { getPlatformShowcaseByKey } from './platformShowcaseModel.mjs'
import { getOpenksPortalUrl } from '../utils/openksPortal'
import { getAuth, persistAuth } from '../utils/auth'

const { Title, Paragraph, Text } = Typography

const PILOT_PLATFORM_SECTION_NAMES = ['整体概况', '数据汇聚', '知识计算', '网链分析', '智能服务']
const PILOT_PLATFORM_CONTENT_TERMS = ['数据资源池', '产业网大图', '四链分析', '头条推送', 'knowledge_fusion', '后续接入']

const ShowcaseHero = ({ activeKey, activeTab, section, onPrimaryAction }) => {
  const contentTerms = activeKey === 'knowledge-computing'
    ? [...PILOT_PLATFORM_CONTENT_TERMS, 'OpenKS 工作台']
    : PILOT_PLATFORM_CONTENT_TERMS

  return (
  <Card className="platform-overview-hero platform-showcase-shell" bodyStyle={{ padding: 0 }}>
    <div className="platform-showcase-hero-grid">
      <div className="platform-showcase-hero-main">
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          <Tag className="platform-overview-hero-tag">{section.eyebrow}</Tag>
          <Title level={1} className="platform-showcase-title">
            {section.headline || activeTab.heroTitle || activeTab.title}
          </Title>
          <Paragraph className="platform-overview-hero-copy">
            {section.summary || activeTab.heroSummary || activeTab.subtitle}
          </Paragraph>
          <div className="platform-showcase-chip-row">
            {PILOT_PLATFORM_SECTION_NAMES.map((item) => (
              <span
                key={item}
                className={`platform-showcase-stage-chip${item === activeTab.title ? ' active' : ''}`}
              >
                {item}
              </span>
            ))}
          </div>
          <Space wrap>
            <Button type="primary" size="large" onClick={onPrimaryAction}>
              {section.actions?.[0]?.label || `进入${activeTab.title}`}
            </Button>
          </Space>
        </Space>
      </div>
      <div className="platform-showcase-hero-side">
        <div className="platform-showcase-section-head">
          <Text className="platform-showcase-eyebrow">当前栏目</Text>
          <Title level={3} style={{ margin: 0 }}>
            {activeTab.title}
          </Title>
          <Paragraph style={{ margin: 0 }}>
            {section.headline}
          </Paragraph>
        </div>
        <Divider style={{ borderColor: 'rgba(14, 42, 64, 0.12)', margin: '14px 0' }} />
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Text className="platform-showcase-eyebrow">展示锚点</Text>
          <div className="platform-showcase-chip-row">
            {contentTerms.map((item) => (
              <span key={item} className="platform-showcase-keyword">
                {item}
              </span>
            ))}
          </div>
        </Space>
      </div>
    </div>
  </Card>
  )
}

const MetricsStrip = ({ metrics = [] }) => (
  <Row gutter={[16, 16]}>
    {metrics.map((item) => (
      <Col key={item.label} xs={24} md={8}>
        <Card className="platform-showcase-metric-card" bodyStyle={{ padding: 20 }}>
          <Space direction="vertical" size={10}>
            <Text className="platform-showcase-metric-label">{item.label}</Text>
            <Title level={3} style={{ margin: 0 }}>
              {item.value}
            </Title>
            <Paragraph style={{ margin: 0 }}>{item.note}</Paragraph>
          </Space>
        </Card>
      </Col>
    ))}
  </Row>
)

const ModuleCard = ({ module, onPlaceholderAction }) => (
  <Card className="platform-showcase-module-card" bodyStyle={{ padding: 20 }}>
    <Space direction="vertical" size={14} style={{ width: '100%' }}>
      <div className="platform-showcase-module-head">
        <div>
          <Text className="platform-showcase-eyebrow">展示模块</Text>
          <Title level={4} style={{ margin: '4px 0 0' }}>
            {module.title}
          </Title>
        </div>
        <Tag className={module.integration === 'pending' ? 'platform-showcase-placeholder-badge' : 'platform-showcase-live-badge'}>
          {module.badge}
        </Tag>
      </div>
      <Paragraph style={{ margin: 0 }}>{module.description}</Paragraph>
      <div className="platform-showcase-bullet-list">
        {module.bullets.map((item) => (
          <div key={item} className="platform-showcase-bullet-item">
            <span className="platform-showcase-bullet-dot" />
            <Text>{item}</Text>
          </div>
        ))}
      </div>
      <Button
        type={module.integration === 'pending' ? 'default' : 'primary'}
        ghost={module.integration === 'pending'}
        icon={<ArrowRightOutlined />}
        onClick={() => onPlaceholderAction(module)}
      >
        {module.integration === 'pending' ? '查看接入说明' : '查看展示说明'}
      </Button>
    </Space>
  </Card>
)

const ModuleGrid = ({ modules = [], onPlaceholderAction }) => (
  <Card bodyStyle={{ padding: 24 }}>
    <div className="platform-showcase-section-head">
      <div>
        <Text className="platform-showcase-eyebrow">模块整理</Text>
        <Title level={3} style={{ margin: '6px 0 0' }}>
          前台展示模块
        </Title>
      </div>
      <Paragraph style={{ margin: 0 }}>
        这里强调页面设计和模块归位，不在前台直接接入后台接口。
      </Paragraph>
    </div>
    <div className="platform-showcase-module-grid">
      {modules.map((module) => (
        <ModuleCard key={module.title} module={module} onPlaceholderAction={onPlaceholderAction} />
      ))}
    </div>
  </Card>
)

const FlowPanel = ({ flow = [] }) => (
  <Card bodyStyle={{ padding: 24 }}>
    <div className="platform-showcase-section-head">
      <div>
        <Text className="platform-showcase-eyebrow">过程展示</Text>
        <Title level={3} style={{ margin: '6px 0 0' }}>
          页面呈现流程
        </Title>
      </div>
      <Paragraph style={{ margin: 0 }}>
        将原本后台执行链路转成适合前台汇报和演示的可视结构。
      </Paragraph>
    </div>
    <div className="platform-showcase-flow-list">
      {flow.map((item, index) => (
        <div key={item.title} className="platform-showcase-flow-item">
          <div className="platform-showcase-flow-index">{String(index + 1).padStart(2, '0')}</div>
          <div>
            <Title level={5} style={{ margin: 0 }}>
              {item.title}
            </Title>
            <Paragraph style={{ margin: '6px 0 0' }}>{item.description}</Paragraph>
          </div>
        </div>
      ))}
    </div>
  </Card>
)

const ContractPanels = ({ contracts = [] }) => {
  if (!contracts.length) return null

  return (
    <Card bodyStyle={{ padding: 24 }}>
      <div className="platform-showcase-section-head">
        <div>
          <Text className="platform-showcase-eyebrow">接口整理</Text>
          <Title level={3} style={{ margin: '6px 0 0' }}>
            接口定义与规范
          </Title>
        </div>
        <Paragraph style={{ margin: 0 }}>
          DataHub、Graphiti 与独立域名入口先明确合同、字段和跳转口径，再逐步替换为真实对接。
        </Paragraph>
      </div>
      <div className="platform-contract-grid">
        {contracts.map((contract) => (
          <div key={contract.title} className="platform-contract-card">
            <div className="platform-contract-head">
              <Title level={5} style={{ margin: 0 }}>
                {contract.title}
              </Title>
              <Tag className="platform-showcase-placeholder-badge">{contract.status}</Tag>
            </div>
            <Text className="platform-contract-endpoint">{contract.endpoint}</Text>
            <Paragraph style={{ margin: '10px 0 0' }}>{contract.summary}</Paragraph>
            <div className="platform-showcase-chip-row">
              {(contract.fields || []).map((field) => (
                <span key={field} className="platform-showcase-keyword">
                  {field}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

const GovernancePanel = ({ items = [] }) => {
  if (!items.length) return null

  return (
    <Card bodyStyle={{ padding: 24 }}>
      <div className="platform-showcase-section-head">
        <div>
          <Text className="platform-showcase-eyebrow">治理口径</Text>
          <Title level={3} style={{ margin: '6px 0 0' }}>
            链路状态与审核
          </Title>
        </div>
        <Paragraph style={{ margin: 0 }}>
          页面上明确哪些链路已经生产化，哪些仅是合同占位，以及产业网图谱要怎么审。
        </Paragraph>
      </div>
      <Space direction="vertical" size={14} style={{ width: '100%' }}>
        {items.map((item) => (
          <div key={item.title} className="platform-governance-card">
            <Title level={5} style={{ margin: 0 }}>
              {item.title}
            </Title>
            <Paragraph style={{ margin: '10px 0 0' }}>{item.summary}</Paragraph>
            <div className="platform-showcase-bullet-list">
              {(item.bullets || []).map((bullet) => (
                <div key={bullet} className="platform-showcase-bullet-item">
                  <span className="platform-showcase-bullet-dot" />
                  <Text>{bullet}</Text>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Space>
    </Card>
  )
}

const OutcomesPanel = ({ keywordTags = [], outcomes = [], actions = [], onAction }) => (
  <Space direction="vertical" size={16} style={{ width: '100%' }}>
    <Card bodyStyle={{ padding: 24 }}>
      <div className="platform-showcase-section-head">
        <div>
          <Text className="platform-showcase-eyebrow">栏目关键词</Text>
          <Title level={3} style={{ margin: '6px 0 0' }}>
            当前展示重点
          </Title>
        </div>
      </div>
      <div className="platform-showcase-chip-row">
        {keywordTags.map((item) => (
          <span key={item} className="platform-showcase-keyword strong">
            {item}
          </span>
        ))}
      </div>
    </Card>

    <Card bodyStyle={{ padding: 24 }}>
      <div className="platform-showcase-section-head">
        <div>
          <Text className="platform-showcase-eyebrow">成果口径</Text>
          <Title level={3} style={{ margin: '6px 0 0' }}>
            前台应该看到什么
          </Title>
        </div>
      </div>
      <div className="platform-showcase-bullet-list">
        {outcomes.map((item) => (
          <div key={item} className="platform-showcase-bullet-item">
            <span className="platform-showcase-bullet-dot" />
            <Text>{item}</Text>
          </div>
        ))}
      </div>
    </Card>

    <Card bodyStyle={{ padding: 24 }}>
      <div className="platform-showcase-section-head">
        <div>
          <Text className="platform-showcase-eyebrow">接入动作</Text>
          <Title level={3} style={{ margin: '6px 0 0' }}>
            后续接入预留
          </Title>
        </div>
        <Paragraph style={{ margin: 0 }}>
          需要外部系统的地方先不接，只在页面上清楚标注后续接入；OpenKS 主前台默认跳到独立域名。
        </Paragraph>
      </div>
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {actions.map((action) => (
          <Button
            key={action.label}
            block
            type={action.type === 'primary' ? 'primary' : 'default'}
            onClick={() => onAction(action)}
          >
            {action.label}
          </Button>
        ))}
      </Space>
    </Card>
  </Space>
)

const PlatformOverviewPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { message } = AntdApp.useApp()

  const activeKey = resolvePlatformTabKey(searchParams.get('tab'))
  const activeTab = useMemo(() => getPlatformTabByKey(activeKey), [activeKey])
  const section = useMemo(() => getPlatformShowcaseByKey(activeKey), [activeKey])

  const handleAction = (action) => {
    if (action?.mode === 'tab' && action?.target) {
      navigate(`/platform?tab=${action.target}`)
      return
    }
    if (action?.mode === 'openks-portal') {
      const auth = getAuth()
      if (auth) {
        persistAuth(auth)
      }
      window.open(getOpenksPortalUrl(action.target || '/'), '_blank', 'noopener,noreferrer')
      return
    }
    if (action?.mode === 'route' && action?.target) {
      navigate(action.target)
      return
    }
    message.info(`${action?.label || '该能力'}：后续接入`)
  }

  const handleModuleAction = (module) => {
    if (module.integration === 'pending') {
      message.info(`${module.title}：后续接入`)
      return
    }
    message.info(`${module.title}：当前为前台展示模块`)
  }

  return (
    <div className="platform-overview-page">
      <Space direction="vertical" size={18} style={{ width: '100%' }}>
        <ShowcaseHero activeKey={activeKey} activeTab={activeTab} section={section} onPrimaryAction={() => handleAction(section.actions?.[0])} />
        <MetricsStrip metrics={section.metrics} />
        <Row gutter={[18, 18]} align="stretch">
          <Col xs={24} xl={16}>
            <Space direction="vertical" size={18} style={{ width: '100%' }}>
              <ModuleGrid modules={section.modules} onPlaceholderAction={handleModuleAction} />
              <ContractPanels contracts={section.contracts} />
              <FlowPanel flow={section.flow} />
            </Space>
          </Col>
          <Col xs={24} xl={8}>
            <Space direction="vertical" size={18} style={{ width: '100%' }}>
              <OutcomesPanel
                keywordTags={section.keywordTags}
                outcomes={section.outcomes}
                actions={section.actions}
                onAction={handleAction}
              />
              <GovernancePanel items={section.governance} />
            </Space>
          </Col>
        </Row>
      </Space>
    </div>
  )
}

export default PlatformOverviewPage
