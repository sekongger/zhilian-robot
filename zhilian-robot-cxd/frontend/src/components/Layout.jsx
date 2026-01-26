import React from 'react'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Space, theme } from 'antd'
import { 
  HomeOutlined, 
  DeploymentUnitOutlined, 
  ExperimentOutlined,
  DatabaseOutlined,
  UserOutlined,
  RobotOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header, Content, Footer } = AntLayout

const Layout = ({ children }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()

  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: '概览' },
    { key: '/graph', icon: <DeploymentUnitOutlined />, label: '图谱探索' },
    { key: '/temporal', icon: <ThunderboltOutlined />, label: '时序分析' },
    { key: '/analysis', icon: <ExperimentOutlined />, label: '智能分析' },
    { key: '/data', icon: <DatabaseOutlined />, label: '数据中心' },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh', background: '#0f172a' }}>
      <Header style={{ 
        position: 'sticky', 
        top: 0, 
        zIndex: 100, 
        width: '100%', 
        display: 'flex', 
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        background: 'rgba(30, 41, 59, 0.9)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid #334155',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)'
      }}>
        {/* Logo 区域 */}
        <div 
          onClick={() => navigate('/')}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '12px', 
            cursor: 'pointer',
            marginRight: '40px',
            transition: 'transform 0.2s ease'
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <div style={{
            width: 38, 
            height: 38, 
            background: `linear-gradient(135deg, #6366f1, #8b5cf6)`,
            borderRadius: '10px',
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            color: 'white', 
            fontSize: '22px',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)'
          }}>
            <RobotOutlined />
          </div>
          <span style={{ 
            fontSize: '19px', 
            fontWeight: 700, 
            background: `linear-gradient(to right, #6366f1, #a855f7)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '0.02em'
          }}>
            智链机器人
          </span>
        </div>

        {/* 菜单区域 */}
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ 
            flex: 1, 
            borderBottom: 'none', 
            background: 'transparent',
            fontSize: '15px',
            fontWeight: 500
          }}
        />

        {/* 右侧用户区域 (预留) */}
        <Space>
           <Avatar 
             style={{ 
               backgroundColor: '#6366f1',
               boxShadow: '0 2px 8px rgba(99, 102, 241, 0.4)'
             }} 
             icon={<UserOutlined />} 
           />
        </Space>
      </Header>

      <Content style={{ 
        padding: '28px', 
        maxWidth: '1600px', 
        width: '100%', 
        margin: '0 auto',
        background: '#0f172a'
      }}>
        <div className="fade-in">
          {children}
        </div>
      </Content>

      <Footer style={{ 
        textAlign: 'center', 
        color: '#64748b', 
        background: '#0f172a',
        borderTop: '1px solid #1e293b',
        padding: '24px 0',
        fontSize: '14px'
      }}>
        <div style={{ marginBottom: 8 }}>
          <span style={{ 
            background: 'linear-gradient(to right, #6366f1, #a855f7)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 600
          }}>
            智链机器人
          </span>
        </div>
        <div style={{ fontSize: 13, opacity: 0.8 }}>
          ©2025 | 大模型驱动的产业链图谱自动构建平台
        </div>
      </Footer>
    </AntLayout>
  )
}

export default Layout