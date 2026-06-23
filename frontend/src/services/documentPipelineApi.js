import apiClient from '../utils/api'

export const documentPipelineService = {
  getStats: (params) => {
    if (!params) {
      return apiClient.get('/api/v1/document-pipeline/stats')
    }
    if (typeof params === 'string') {
      return apiClient.get('/api/v1/document-pipeline/stats', { params: { doc_type: params } })
    }
    return apiClient.get('/api/v1/document-pipeline/stats', { params })
  },
  getRecords: (params = {}) => apiClient.get('/api/v1/document-pipeline/records', { params }),
  batchProcess: (limit = 10) => apiClient.post('/api/v1/ingest/batch', { limit }),
  scenarioCollaboration: (company) => apiClient.get('/api/v1/document-pipeline/scenarios/collaboration', { params: { company } }),
  scenarioTechMatch: (keyword) => apiClient.get('/api/v1/document-pipeline/scenarios/tech-match', { params: { keyword } }),
  scenarioProvenance: (title) => apiClient.get('/api/v1/document-pipeline/scenarios/provenance', { params: { title } }),
}
