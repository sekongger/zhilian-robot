import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ConfigProvider, App as AntdApp, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import GraphPage from './pages/GraphPage'
import AnalysisPage from './pages/AnalysisPage'
import DataManagePage from './pages/DataManagePage'
import TemporalAnalysisPage from './pages/TemporalAnalysisPage'

// 自定义深色主题配�?
const themeConfig = {
  algorithm: theme.darkAlgorithm, // 启用深色算法
  token: {
    colorPrimary: '#6366f1', // 靛蓝�?
    colorInfo: '#3b82f6',
    colorSuccess: '#22c55e',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorBgContainer: '#1e293b',
    colorBgElevated: '#0f172a',
    colorBorder: '#334155',
    colorText: '#e2e8f0',
    colorTextSecondary: '#94a3b8',
    borderRadius: 8,
    wireframe: false,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#1e293b',
      bodyBg: '#0f172a',
      siderBg: '#1e293b',
    },
    Card: {
      paddingLG: 24,
      colorBgContainer: '#1e293b',
      colorBorderSecondary: '#334155',
    },
    Button: {
      controlHeight: 36,
      controlHeightLG: 44,
      colorBgContainer: '#1e293b',
    },
    Input: {
      colorBgContainer: '#1e293b',
      colorBorder: '#334155',
    },
    Select: {
      colorBgContainer: '#1e293b',
      colorBorder: '#334155',
    },
    Table: {
      colorBgContainer: '#1e293b',
      colorBorderSecondary: '#334155',
    },
  }
}

function App() {
  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <AntdApp>
        <Router>
          <Layout>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/graph" element={<GraphPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/temporal" element={<TemporalAnalysisPage />} />
              <Route path="/data" element={<DataManagePage />} />
            </Routes>
          </Layout>
        </Router>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
