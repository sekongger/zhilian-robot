import apiClient from '../utils/api'

export const openksApi = {
  getModules: (params = {}) => apiClient.get('/api/v1/openks/modules', { params }),
  getModule: (name) => apiClient.get(`/api/v1/openks/modules/${encodeURIComponent(name)}`),
  getOverview: () => apiClient.get('/api/v1/openks/overview'),
  getNewsKgStatus: () => apiClient.get('/api/v1/openks/news-kg/status'),
  buildNewsKg: (params = {}) => apiClient.post('/api/v1/openks/news-kg/build', null, { params }),
  queryNewsKg: (payload = {}) => apiClient.post('/api/v1/openks/news-kg/query', payload),
}

export default openksApi
