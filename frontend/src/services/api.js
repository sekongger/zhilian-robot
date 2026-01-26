import apiClient from '../utils/api'

// NLP分析相关API
export const nlpService = {
  // 分析文本
  analyzeText: (data) => {
    return apiClient.post('/api/v1/nlp/analyze', data)
  },

  // 使用大模型分析文本
  analyzeTextWithLLM: (data) => {
    return apiClient.post('/api/v1/nlp/analyze-llm', data)
  },

  // 获取实体类别
  getEntityCategories: () => {
    return apiClient.get('/api/v1/nlp/entities/categories')
  },

  // 获取关系类型
  getRelationTypes: () => {
    return apiClient.get('/api/v1/nlp/relations/types')
  }
}

// 图谱相关API
export const graphService = {
  // 构建图谱(从文本重新分析)
  buildGraph: (text, useLLM = false) => {
    return apiClient.post('/api/v1/graph/build', null, {
      params: { text, use_llm: useLLM }
    })
  },

  // 保存已分析的数据到图谱
  saveToGraph: (entities, relations) => {
    return apiClient.post('/api/v1/graph/save', {
      entities,
      relations
    })
  },

  // 查询产业链
  queryIndustryChain: (data) => {
    return apiClient.post('/api/v1/graph/query', data)
  },

  // 获取企业关系
  getCompanyRelations: (companyName, depth = 2) => {
    return apiClient.get(`/api/v1/graph/company/${encodeURIComponent(companyName)}`, {
      params: { depth }
    })
  },

  // 获取统计信息
  getStatistics: () => {
    return apiClient.get('/api/v1/graph/statistics')
  },

  // 清空图谱
  clearGraph: () => {
    return apiClient.delete('/api/v1/graph/clear')
  }
}

// 数据采集相关API
export const dataService = {
  // 获取文章列表
  getArticles: (params = {}) => {
    return apiClient.get('/api/v1/data/articles', { params })
  },

  // 获取数据统计
  getDataStatistics: () => {
    return apiClient.get('/api/v1/data/statistics')
  },

  // 手动触发关键词爬取
  crawlKeyword: (keyword) => {
    return apiClient.post('/api/v1/data/crawl', null, {
      params: { keyword }
    })
  },

  // 手动触发RSS更新
  updateRss: () => {
    return apiClient.post('/api/v1/data/rss/update')
  },

  // 处理文章(提取实体关系并保存到图谱)
  processArticle: (articleId) => {
    return apiClient.post(`/api/v1/data/process/${articleId}`)
  },

  // 批量处理文章
  batchProcessArticles: (articleIds) => {
    return apiClient.post('/api/v1/data/process/batch', {
      article_ids: articleIds
    })
  },

  // 删除文章
  deleteArticle: (articleId) => {
    return apiClient.delete(`/api/v1/data/articles/${articleId}`)
  },

  // 批量删除文章
  batchDeleteArticles: (articleIds) => {
    return apiClient.post('/api/v1/data/articles/delete/batch', {
      article_ids: articleIds
    })
  },

  // 清理旧数据
  cleanupOldData: (days = 30) => {
    return apiClient.delete('/api/v1/data/cleanup', {
      params: { days }
    })
  },

  // 获取任务历史
  getTaskHistory: (params = {}) => {
    return apiClient.get('/api/v1/data/tasks/history', { params })
  }
}

// 数据接入相关API (新功能)
export const ingestionService = {
  // 上传文件
  uploadFile: (file, sourceName = 'file_upload', processImmediately = true) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_name', sourceName)
    formData.append('process_immediately', processImmediately)
    return apiClient.post('/api/v1/ingestion/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 批量上传文件
  uploadBatch: (files, sourceName = 'batch_upload') => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    formData.append('source_name', sourceName)
    return apiClient.post('/api/v1/ingestion/upload/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 获取原始数据记录列表
  getRecords: (params = {}) => {
    return apiClient.get('/api/v1/ingestion/records', { params })
  },

  // 获取单条记录
  getRecord: (recordId) => {
    return apiClient.get(`/api/v1/ingestion/records/${recordId}`)
  },

  // 下载原始文件
  downloadRecord: (recordId) => {
    return apiClient.get(`/api/v1/ingestion/records/${recordId}/download`)
  },

  // 处理记录(NLP提取)
  processRecord: (recordId) => {
    return apiClient.post(`/api/v1/ingestion/records/${recordId}/process`)
  },

  // 获取接入统计
  getStats: () => {
    return apiClient.get('/api/v1/ingestion/stats')
  }
}

// 实体操作相关API
export const entityActionsService = {
  // 添加到监控
  addToMonitor: (entityData) => {
    return apiClient.post('/api/v1/entity-actions/monitor/add', entityData)
  },

  // 从监控移除
  removeFromMonitor: (entityId) => {
    return apiClient.delete(`/api/v1/entity-actions/monitor/remove/${entityId}`)
  },

  // 获取监控列表
  getMonitorList: () => {
    return apiClient.get('/api/v1/entity-actions/monitor/list')
  },

  // 研判溯源
  investigate: (entityId, depth = 2) => {
    return apiClient.post('/api/v1/entity-actions/investigate', {
      entity_id: entityId,
      depth: depth
    })
  },

  // 生成AI简报
  generateReport: (entityId) => {
    return apiClient.post('/api/v1/entity-actions/generate-report', {
      entity_id: entityId
    })
  },

  // 导出原始数据
  exportData: (entityId) => {
    return apiClient.post('/api/v1/entity-actions/export-data', {
      entity_id: entityId
    })
  },

  // 屏蔽实体
  hideEntity: (entityId) => {
    return apiClient.post('/api/v1/entity-actions/hide-entity', {
      entity_id: entityId
    })
  }
}

// 默认导出所有服务
export default {
  nlp: nlpService,
  graph: graphService,
  data: dataService,
  ingestion: ingestionService,
  entityActions: entityActionsService
}
