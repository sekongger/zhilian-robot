import apiClient from '../utils/api'

export const workflowApi = {
  runNewsWorkflow: (payload = {}) => {
    return apiClient.post('/api/v1/workflow/news/run', payload)
  },

  getRun: (runId) => {
    return apiClient.get(`/api/v1/workflow/news/runs/${encodeURIComponent(runId)}`)
  },

  getRunStepDetail: (runId, stepKey) => {
    return apiClient.get(`/api/v1/workflow/news/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}`)
  },

  getLatestRun: (projectId = 1) => {
    return apiClient.get('/api/v1/workflow/news/latest', {
      params: { project_id: projectId }
    })
  },

  getHistory: (projectId = 1, limit = 20) => {
    return apiClient.get('/api/v1/workflow/news/history', {
      params: { project_id: projectId, limit }
    })
  },

  collectStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/collect', payload)
  },

  processStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/process', payload)
  },

  extractStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/extract', payload)
  },

  modelStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/model', payload)
  },

  executeStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/execute', payload)
  },

  applyStep: (payload) => {
    return apiClient.post('/api/v1/workflow/news/steps/apply', payload)
  }
}

export default workflowApi
