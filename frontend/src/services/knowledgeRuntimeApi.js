import apiClient from '../utils/api'

export const knowledgeRuntimeApi = {
  getRuns: (params = {}) => apiClient.get('/api/v1/runs', { params }),
  getRun: (runId) => apiClient.get(`/api/v1/runs/${encodeURIComponent(runId)}`),
  getArtifacts: (params = {}) => apiClient.get('/api/v1/artifacts', { params }),
  getArtifact: (artifactId) => apiClient.get(`/api/v1/artifacts/${encodeURIComponent(artifactId)}`),
  getReleases: (params = {}) => apiClient.get('/api/v1/releases', { params }),
  getRelease: (releaseId) => apiClient.get(`/api/v1/releases/${encodeURIComponent(releaseId)}`),
  createRelease: (payload) => apiClient.post('/api/v1/releases', payload),
  submitReview: (releaseId, payload = {}) => apiClient.post(`/api/v1/releases/${encodeURIComponent(releaseId)}/submit-review`, payload),
  approveRelease: (releaseId, payload = {}) => apiClient.post(`/api/v1/releases/${encodeURIComponent(releaseId)}/approve`, payload),
  activateRelease: (releaseId, payload = {}) => apiClient.post(`/api/v1/releases/${encodeURIComponent(releaseId)}/activate`, payload),
  rollbackRelease: (releaseId, payload = {}) =>
    apiClient.post(`/api/v1/releases/${encodeURIComponent(releaseId)}/rollback`, payload),
}

export default knowledgeRuntimeApi
