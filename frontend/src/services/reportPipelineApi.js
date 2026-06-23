import axios from 'axios'

const API_BASE = '/api/v1'

/**
 * 研报处理管道 API 服务
 */
export const reportPipelineService = {
  /**
   * 获取研报列表
   * @param {Object} params - 查询参数
   * @param {number} params.limit - 每页数量
   * @param {number} params.offset - 偏移量
   * @param {string} params.status - 状态筛选
   * @param {string} params.industry - 行业筛选
   * @param {string} params.institution - 机构筛选
   */
  listReports: async (params = {}) => {
    const res = await axios.get(`${API_BASE}/report-pipeline/list`, { params })
    return res.data
  },

  /**
   * 创建研报记录
   * @param {Object} data - 研报数据
   */
  createReport: async (data) => {
    const res = await axios.post(`${API_BASE}/report-pipeline/create`, data)
    return res.data
  },

  /**
   * 上传研报PDF
   * @param {FormData} formData - 包含PDF文件的表单数据
   */
  uploadReport: async (formData) => {
    const res = await axios.post(`${API_BASE}/report-pipeline/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  /**
   * 处理单篇研报
   * @param {string} id - 研报ID
   */
  processReport: async (id) => {
    const res = await axios.post(`${API_BASE}/report-pipeline/process/${id}`)
    return res.data
  },

  /**
   * 批量处理研报
   * @param {number} limit - 处理数量上限
   */
  batchProcess: async (limit = 10) => {
    const res = await axios.post(`${API_BASE}/report-pipeline/batch-process`, { limit })
    return res.data
  },

  /**
   * 获取研报抽取的知识
   * @param {string} id - 研报ID
   */
  getKnowledge: async (id) => {
    const res = await axios.get(`${API_BASE}/report-pipeline/knowledge/${id}`)
    return res.data
  },

  /**
   * 获取研报详情
   * @param {string} id - 研报ID
   */
  getDetail: async (id) => {
    const res = await axios.get(`${API_BASE}/report-pipeline/detail/${id}`)
    return res.data
  },

  /**
   * 获取研报统计数据
   */
  getStats: async () => {
    const res = await axios.get(`${API_BASE}/report-pipeline/stats`)
    return res.data
  },

  /**
   * 导入研报（从外部源）
   * @param {Object} params - 导入参数
   */
  importReports: async (params = {}) => {
    const res = await axios.post(`${API_BASE}/report-pipeline/import`, null, { params })
    return res.data
  },
}

export default reportPipelineService
