import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_URL || '').trim()
const API_BASE_URL = apiBaseUrl.length > 0 ? apiBaseUrl : ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,  // 增加到 5 分钟,首次加载模型需要时间
  headers: {
    'Content-Type': 'application/json',
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default apiClient
