import apiClient from '../utils/api'

export const openspgDemoService = {
  getHeadlines: (params = {}) => {
    return apiClient.get('/api/v1/openspg-demo/headlines', { params })
  },

  getHeadlineDetail: (eventId, params = {}) => {
    return apiClient.get(`/api/v1/openspg-demo/headlines/${encodeURIComponent(eventId)}`, { params })
  },

  getEngineSnapshot: (projectId = 1) => {
    return apiClient.get('/api/v1/openspg-demo/engine/snapshot', {
      params: { project_id: projectId }
    })
  },

  getEngineHealth: (projectId = 1) => {
    return apiClient.get('/api/v1/openspg-demo/engine/health', {
      params: { project_id: projectId }
    })
  },

  submitEngineBuilderJob: (payload) => {
    return apiClient.post('/api/v1/openspg-demo/engine/builder/submit', payload)
  },

  getBridgeBatchPreview: (params = {}) => {
    return apiClient.get('/api/v1/openspg-demo/bridge/batch-preview', { params })
  },

  getBridgeStatus: () => {
    return apiClient.get('/api/v1/openspg-demo/bridge/status')
  },

  runBridgeBatch: (payload = {}) => {
    return apiClient.post('/api/v1/openspg-demo/bridge/run', payload)
  },

  pullRealRss: (payload = {}) => {
    return apiClient.post('/api/v1/openspg-demo/ingest/rss', payload)
  },

  getBridgeExportUrl: (params = {}) => {
    const search = new URLSearchParams()
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        search.set(key, String(value))
      }
    })
    const qs = search.toString()
    return `/api/v1/openspg-demo/bridge/export.jsonl${qs ? `?${qs}` : ''}`
  },

  getBridgeRunDownloadUrl: (runId) => {
    return `/api/v1/openspg-demo/bridge/runs/${encodeURIComponent(runId)}/download`
  },

  getModelStudioSchemaTemplate: () => {
    return apiClient.get('/api/v1/openspg-demo/model-studio/schema/template')
  },

  getModelStudioSchemaCurrent: (projectId = 1) => {
    return apiClient.get('/api/v1/openspg-demo/model-studio/schema/current', {
      params: { project_id: projectId }
    })
  },

  getModelStudioActiveSchema: (projectId = 1) => {
    return apiClient.get('/api/v1/openspg-demo/model-studio/schema/active', {
      params: { project_id: projectId }
    })
  },

  activateModelStudioSchema: (payload) => {
    return apiClient.post('/api/v1/openspg-demo/model-studio/schema/activate', payload)
  },

  applyModelStudioSchema: (payload) => {
    return apiClient.post('/api/v1/openspg-demo/model-studio/schema/apply', payload)
  },

  submitModelStudioExtraction: (payload) => {
    return apiClient.post('/api/v1/openspg-demo/model-studio/extraction/submit', payload)
  },

  submitModelStudioExtractionFile: (formData) => {
    return apiClient.post('/api/v1/openspg-demo/model-studio/extraction/submit-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getModelStudioExtractionStatus: (projectId, jobId) => {
    return apiClient.get('/api/v1/openspg-demo/model-studio/extraction/status', {
      params: { project_id: projectId, job_id: jobId }
    })
  },

  getModelStudioExtractionSample: (projectId, jobId) => {
    return apiClient.get('/api/v1/openspg-demo/model-studio/extraction/sample', {
      params: { project_id: projectId, job_id: jobId }
    })
  },

  runNewsWorkflow: (payload = {}) => {
    return apiClient.post('/api/v1/openspg-demo/workflow/news/run', payload)
  },

  getNewsWorkflowRun: (runId) => {
    return apiClient.get(`/api/v1/openspg-demo/workflow/news/runs/${encodeURIComponent(runId)}`)
  },

  getLatestNewsWorkflowRun: (projectId = 1) => {
    return apiClient.get('/api/v1/openspg-demo/workflow/news/latest', {
      params: { project_id: projectId }
    })
  },

  getNewsWorkflowHistory: (projectId = 1, limit = 20) => {
    return apiClient.get('/api/v1/openspg-demo/workflow/news/history', {
      params: { project_id: projectId, limit }
    })
  }
}

export default openspgDemoService
