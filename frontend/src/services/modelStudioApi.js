import apiClient from '../utils/api'

export const modelStudioApi = {
  getCurrentSchema: (projectId = 1) => {
    return apiClient.get('/api/v1/model-studio/schema/current', {
      params: { project_id: projectId }
    })
  }
}

export default modelStudioApi
