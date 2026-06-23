import apiClient from '../utils/api'

export const resourceHubApi = {
  getSummary: () => apiClient.get('/api/v1/resource-hub/summary'),
  getResources: () => apiClient.get('/api/v1/resource-hub/resources'),
  getResourceDetail: (resourceKey) => apiClient.get(`/api/v1/resource-hub/resources/${encodeURIComponent(resourceKey)}`),
  getMetricRecords: (resourceKey, metricKey, params = {}) =>
    apiClient.get(`/api/v1/resource-hub/resources/${encodeURIComponent(resourceKey)}/metrics/${encodeURIComponent(metricKey)}/records`, { params }),
}

export default resourceHubApi
