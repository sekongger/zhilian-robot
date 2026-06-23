import apiClient from '../utils/api'

export const openApiService = {
  getHeadlines: (params = {}) => {
    return apiClient.get('/api/v1/open/applications/headlines', { params })
  },

  queryKnowledge: (payload) => {
    return apiClient.post('/api/v1/open/knowledge/query', payload)
  },

  batchQueryKnowledge: (payload) => {
    return apiClient.post('/api/v1/open/knowledge/query/batch', payload)
  },

  getTrace: (traceId) => {
    return apiClient.get(`/api/v1/open/knowledge/trace/${encodeURIComponent(traceId)}`)
  }
}

export default openApiService
