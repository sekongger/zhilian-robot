import React from 'react'
import { Layout as AntLayout, Avatar, Button, Space, Tag, Typography } from 'antd'
import { DatabaseZap, Layers3, Network, ArrowLeftRight, ShieldCheck } from 'lucide-react'
import { useLocation, useNavigate, Outlet } from 'react-router-dom'
import { logout, getAuth } from '../utils/auth'
import { getOpenksPortalUrl } from '../utils/openksPortal'
import { getPlatformPortalUrl } from '../utils/platformPortal'

const { Header, Content, Footer } = AntLayout
const { Text } = Typography

const OPENKS_NAV_ITEMS = [
  { key: 'overview', label: '总览', query: 'overview', icon: <Layers3 size={16} /> },
  { key: 'schema', label: 'Schema', query: 'schema', icon: <DatabaseZap size={16} /> },
  { key: 'modules', label: '模块', query: 'modules', icon: <Network size={16} /> },
  { key: 'chain', label: '主链', query: 'chain', icon: <ArrowLeftRight size={16} /> },
  { key: 'results', label: '结果', query: 'results', icon: <ShieldCheck size={16} /> },
]

function currentTab(search) {
  const tab = new URLSearchParams(search).get('tab')
  return OPENKS_NAV_ITEMS.some((item) => item.query === tab) ? tab : 'overview'
}

const OpenKSLayout = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const activeTab = currentTab(location.search)
  const auth = getAuth()

  return (
    <AntLayout className="openks-shell">
      <Header className="openks-shell-header">
        <div className="openks-shell-brand" onClick={() => navigate('/openks/workbench?tab=overview')}>
          <div className="openks-shell-logo">OK</div>
          <div className="openks-shell-brand-copy">
            <span className="openks-shell-brand-title">OpenKS 知识计算工作台</span>
            <span className="openks-shell-brand-subtitle">独立于中试平台的构建与查询入口</span>
          </div>
        </div>

        <Space size={12} wrap>
          <Tag className="openks-shell-tag">独立部署入口</Tag>
          <Button onClick={() => { window.location.href = getPlatformPortalUrl('/platform?tab=knowledge-computing') }}>
            返回中试平台
          </Button>
          <Avatar className="openks-shell-avatar">{String(auth?.user || 'admin').slice(0, 1).toUpperCase()}</Avatar>
          <Button type="text" className="openks-shell-logout" onClick={() => { logout(); window.location.href = '/login' }}>
            退出
          </Button>
        </Space>
      </Header>

      <div className="openks-shell-nav">
        {OPENKS_NAV_ITEMS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`openks-shell-nav-item${activeTab === item.query ? ' active' : ''}`}
            onClick={() => navigate(`/openks/workbench?tab=${item.query}`)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
        <a className="openks-shell-nav-link" href={getOpenksPortalUrl('/')}>
          外部门户地址
        </a>
      </div>

      <Content className="openks-shell-content">
        <div className="fade-in">{children || <Outlet />}</div>
      </Content>

      <Footer className="openks-shell-footer">
        <Text>OpenKS 独立工作台 | Schema / KG / Production Chain / Runtime Results</Text>
      </Footer>
    </AntLayout>
  )
}

export default OpenKSLayout
