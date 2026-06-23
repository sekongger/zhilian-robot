import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntdApp, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import Layout from './components/Layout'
import OpenKSLayout from './components/OpenKSLayout'
import RequireAuth from './components/RequireAuth'
import HomePage from './pages/HomePage'
import GraphPage from './pages/GraphPage'
import AnalysisPage from './pages/AnalysisPage'
import DataManagePage from './pages/DataManagePage'
import TemporalAnalysisPage from './pages/TemporalAnalysisPage'
import StorageArchitecturePage from './pages/StorageArchitecturePage'
import DocumentPipelinePage from './pages/DocumentPipelinePage'
import LoginPage from './pages/LoginPage'
import KAGWorkflowPage from './pages/KAGWorkflowPage'
import OpenSPGModelStudioPage from './pages/OpenSPGModelStudioPage'
import WorkflowWorkbenchPage from './pages/WorkflowWorkbenchPage'
import ModelStudioPage from './pages/ModelStudioPage'
import DataEvidencePage from './pages/DataEvidencePage'
import ApplicationCenterPage from './pages/ApplicationCenterPage'
import IndustryQAAgentPage from './pages/IndustryQAAgentPage'
import PlatformOverviewPage from './pages/PlatformOverviewPage'
import OpenKSWorkbenchPage from './pages/OpenKSWorkbenchPage'
import OperatorWorkbenchPage from './pages/OperatorWorkbenchPage'
import NewsHeatRankingsPage from './pages/NewsHeatRankingsPage'

// 浅色交互主题
const themeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#0b6e99',
    colorInfo: '#1c7ed6',
    colorSuccess: '#2f9e44',
    colorWarning: '#d98e04',
    colorError: '#d94841',
    colorBgBase: '#f4f7fb',
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBorder: '#d7e0ea',
    colorText: '#14213d',
    colorTextSecondary: '#52607a',
    borderRadius: 10,
    wireframe: false,
    fontFamily: "'Source Han Sans SC', 'PingFang SC', 'Noto Sans SC', sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      bodyBg: '#f4f7fb',
      siderBg: '#ffffff',
    },
    Card: {
      paddingLG: 24,
      colorBgContainer: '#ffffff',
      colorBorderSecondary: '#d7e0ea',
    },
    Button: {
      controlHeight: 36,
      controlHeightLG: 44,
    },
  }
}

function App() {
  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      <AntdApp>
        <Router>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RequireAuth>
                  <OpenKSLayout />
                </RequireAuth>
              }
            >
              <Route path="/openks" element={<Navigate to="/openks/workbench?tab=overview" replace />} />
              <Route path="/openks/workbench" element={<OpenKSWorkbenchPage />} />
            </Route>
            <Route
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            >
              <Route path="/" element={<Navigate to="/platform?tab=overview" replace />} />
              <Route path="/platform" element={<PlatformOverviewPage />} />
              <Route path="/home" element={<HomePage />} />
              <Route path="/workflow" element={<WorkflowWorkbenchPage />} />
              <Route path="/model-studio" element={<ModelStudioPage />} />
              <Route path="/data-evidence" element={<DataEvidencePage />} />
              <Route path="/applications" element={<ApplicationCenterPage />} />
              <Route path="/operator-workbench" element={<OperatorWorkbenchPage />} />
              <Route path="/news-heat-rankings" element={<NewsHeatRankingsPage />} />
              <Route path="/agent/industry-qa" element={<IndustryQAAgentPage />} />

              <Route path="/document" element={<Navigate to="/data-evidence" replace />} />
              <Route path="/kag-workflow" element={<Navigate to="/workflow" replace />} />
              <Route path="/openspg-model-studio" element={<Navigate to="/model-studio" replace />} />

              <Route path="/ontology" element={<StorageArchitecturePage />} />
              <Route path="/graph" element={<GraphPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/temporal" element={<TemporalAnalysisPage />} />
              <Route path="/data" element={<DataManagePage />} />
              <Route path="/legacy/document-pipeline" element={<DocumentPipelinePage />} />
              <Route path="/legacy/kag-workflow" element={<KAGWorkflowPage />} />
              <Route path="/legacy/model-studio" element={<OpenSPGModelStudioPage />} />
              <Route path="/openspg-kag-headlines" element={<Navigate to="/workflow" replace />} />
              <Route path="/openspg-kag-headlines/events/:eventId" element={<Navigate to="/workflow" replace />} />
              <Route path="*" element={<Navigate to="/platform?tab=overview" replace />} />
            </Route>
          </Routes>
        </Router>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
