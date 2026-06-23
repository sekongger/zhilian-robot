import apiClient from '../utils/api'

export const operatorWorkbenchApi = {
  getOverview: () => apiClient.get('/api/v1/operator-workbench/overview'),
  getCatalog: () => apiClient.get('/api/v1/operator-workbench/catalog'),
  getPipelines: () => apiClient.get('/api/v1/operator-workbench/pipelines'),
  getPublishedPipelines: () => apiClient.get('/api/v1/operator-workbench/published'),
  validatePipeline: (operators) => apiClient.post('/api/v1/operator-workbench/validate', { operators }),
  executePreview: (payload) => apiClient.post('/api/v1/operator-workbench/execute-preview', payload),
  publishPipeline: (payload) => apiClient.post('/api/v1/operator-workbench/publish', payload),
}

export default operatorWorkbenchApi
