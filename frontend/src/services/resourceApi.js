import apiClient from '../utils/api'

export const resourceApi = {
  lookupEvidence: (params = {}) => {
    return apiClient.get('/api/v1/resource/evidence/lookup', { params })
  },
}

export default resourceApi
