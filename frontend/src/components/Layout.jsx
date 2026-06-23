import React from 'react'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space } from 'antd'
import {
  AppstoreOutlined,
  BuildOutlined,
  DatabaseOutlined,
  MessageOutlined,
  UserOutlined,
  RobotOutlined,
  RadarChartOutlined,
  ApiOutlined,
  ApartmentOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { logout, getAuth } from '../utils/auth'
import { PLATFORM_TABS, resolvePlatformTabKey } from '../pages/platformTabs.mjs'

const { Header, Content, Footer } = AntLayout

const tabIconMap = {
  overview: <AppstoreOutlined />,
  'data-hub': <DatabaseOutlined />,
  'knowledge-computing': <BuildOutlined />,
  'chain-analysis': <RadarChartOutlined />,
  'intelligent-service': <MessageOutlined />,
}

const routeToMenuKey = (pathname, search) => {
  if (pathname.startsWith('/platform')) {
    const currentTab = resolvePlatformTabKey(new URLSearchParams(search).get('tab'))
    return `/platform?tab=${currentTab}`
  }
  if (pathname.startsWith('/operator-workbench')) {
    return '/operator-workbench'
  }
  if (pathname.startsWith('/news-heat-rankings')) {
    return '/news-heat-rankings'
  }
  if (pathname.startsWith('/workflow') || pathname.startsWith('/model-studio') || pathname.startsWith('/openspg-model-studio')) {
    return '/platform?tab=knowledge-computing'
  }
  if (pathname.startsWith('/data-evidence') || pathname.startsWith('/document') || pathname.startsWith('/data')) {
    return '/platform?tab=data-hub'
  }
  if (pathname.startsWith('/graph') || pathname.startsWith('/analysis') || pathname.startsWith('/temporal')) {
    return '/platform?tab=chain-analysis'
  }
  if (pathname.startsWith('/applications') || pathname.startsWith('/agent/industry-qa')) {
    return '/applications'
  }
  return '/platform?tab=overview'
}

const Layout = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const selectedMenuKey = routeToMenuKey(location.pathname, location.search)

  const menuItems = [
    ...PLATFORM_TABS.map((item) => ({
      key: `/platform?tab=${item.key}`,
      icon: tabIconMap[item.key],
      label: item.title,
    })),
    { key: '/operator-workbench', icon: <ApartmentOutlined />, label: '知识计算工作台' },
    { key: '/news-heat-rankings', icon: <FireOutlined />, label: '资讯热度榜' },
    { key: '/applications', icon: <ApiOutlined />, label: '应用中心' },
  ]

  const auth = getAuth()
  const menu = {
    items: [
      {
        key: 'logout',
        label: '退出登录',
        onClick: () => {
          logout()
          navigate('/login')
        },
      },
    ],
  }

  return (
    <AntLayout style={{ minHeight: '100vh', background: 'var(--bg-page)' }}>
      <Header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: 'rgba(255, 255, 255, 0.88)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid var(--border-subtle)',
          boxShadow: '0 4px 16px rgba(15, 40, 65, 0.06)'
        }}
      >
        <div
          onClick={() => navigate('/platform?tab=overview')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            cursor: 'pointer',
            marginRight: 20,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              fontSize: 22,
              background: 'linear-gradient(135deg, #0b6e99 0%, #1c7ed6 100%)',
              boxShadow: '0 8px 18px rgba(28, 126, 214, 0.22)',
            }}
          >
            <RobotOutlined />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
            <span style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-primary)' }}>
              浙大AI产业知识中心实验平台
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              整体概况 / 数据汇聚 / 知识计算 / 网链分析 / 智能服务
            </span>
          </div>
        </div>

        <Menu
          mode="horizontal"
          selectedKeys={[selectedMenuKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            flex: 1,
            minWidth: 0,
            borderBottom: 'none',
            background: 'transparent',
            fontSize: 14,
            fontWeight: 600,
          }}
        />

        <Space>
          <Dropdown menu={menu} placement="bottomRight" trigger={['click']}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar
                style={{
                  backgroundColor: '#0b6e99',
                  boxShadow: '0 2px 8px rgba(11, 110, 153, 0.2)'
                }}
                icon={<UserOutlined />}
              />
              <span style={{ color: 'var(--text-primary)', fontSize: 12 }}>{auth?.user || 'admin'}</span>
            </Space>
          </Dropdown>
        </Space>
      </Header>

      <Content
        style={{
          padding: '20px',
          maxWidth: '1600px',
          width: '100%',
          margin: '0 auto',
          background: 'var(--bg-page)',
        }}
      >
        <div className="fade-in">{children || <Outlet />}</div>
      </Content>

      <Footer
        style={{
          textAlign: 'center',
          color: 'var(--text-secondary)',
          background: 'var(--bg-page)',
          borderTop: '1px solid var(--border-subtle)',
          padding: '16px 0',
          fontSize: 13,
        }}
      >
        ©2026 浙江大学AI产业知识中心 | OpenSPG-First Platform
      </Footer>
    </AntLayout>
  )
}

export default Layout
