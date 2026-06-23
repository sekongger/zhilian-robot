import apiClient from '../utils/api'

export const platformOverviewApi = {
  getOverview: (stage) =>
    apiClient.get('/api/v1/platform/overview', {
      params: stage ? { stage } : {},
    }),
}

export default platformOverviewApi
