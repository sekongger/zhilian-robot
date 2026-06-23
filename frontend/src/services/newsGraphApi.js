import apiClient from '../utils/api'

export const newsGraphApi = {
  getHeatRankings: (params = {}) => apiClient.get('/api/v1/news-graph/heat-rankings', { params }),
  calculateHeatRankings: (payload = {}) => apiClient.post('/api/v1/news-graph/heat-rankings/calculate', payload),
}

export default newsGraphApi
