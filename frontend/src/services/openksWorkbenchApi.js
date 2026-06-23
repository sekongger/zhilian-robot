import apiClient from '../utils/api'

export const openksWorkbenchApi = {
  getOverview: () => apiClient.get('/api/v1/openks/overview'),
  getModules: () => apiClient.get('/api/v1/openks/modules'),
  getWorkflowLatest: (projectId = 1) => apiClient.get('/api/v1/workflow/news/latest', { params: { project_id: projectId } }),
  getWorkflowStepDetail: (runId, stepKey) => apiClient.get(`/api/v1/workflow/news/runs/${encodeURIComponent(runId)}/steps/${encodeURIComponent(stepKey)}`),
  runWorkflowModel: (payload = {}) => apiClient.post('/api/v1/workflow/news/steps/model', payload),
  runWorkflowExtract: (payload = {}) => apiClient.post('/api/v1/workflow/news/steps/extract', payload),
  runWorkflowExecute: (payload = {}) => apiClient.post('/api/v1/workflow/news/steps/execute', payload),
  getRuntimeRuns: (params = {}) => apiClient.get('/api/v1/runs', { params }),
  getRuntimeArtifacts: (params = {}) => apiClient.get('/api/v1/artifacts', { params }),
  getRuntimeReleases: (params = {}) => apiClient.get('/api/v1/releases', { params }),
}

export default openksWorkbenchApi
