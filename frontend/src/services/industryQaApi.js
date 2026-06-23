import apiClient from '../utils/api'

export const industryQaApi = {
  createSession: (payload = {}) => {
    return apiClient.post('/api/v1/agent/industry-qa/sessions', payload)
  },

  getSessions: () => {
    return apiClient.get('/api/v1/agent/industry-qa/sessions')
  },

  deleteSession: (sessionId) => {
    return apiClient.delete(`/api/v1/agent/industry-qa/sessions/${encodeURIComponent(sessionId)}`)
  },

  chat: (payload) => {
    return apiClient.post('/api/v1/agent/industry-qa/chat', payload)
  },

  chatStream: async (payload, handlers = {}) => {
    const response = await fetch('/api/v1/agent/industry-qa/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || `HTTP ${response.status}`)
    }
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let doneReceived = false
    if (!reader) return

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        const line = part.split('\n').find((item) => item.startsWith('data: '))
        if (!line) continue
        const payload = JSON.parse(line.slice(6))
        if (payload.type === 'meta') handlers.onMeta?.(payload)
        if (payload.type === 'delta') handlers.onDelta?.(payload)
        if (payload.type === 'error') throw new Error(payload.message || '问答流异常中断')
        if (payload.type === 'done') {
          doneReceived = true
          handlers.onDone?.(payload)
        }
      }
    }
    if (!doneReceived) {
      throw new Error('流式响应提前结束，请稍后重试')
    }
  },

  getMessages: (sessionId) => {
    return apiClient.get(`/api/v1/agent/industry-qa/sessions/${encodeURIComponent(sessionId)}/messages`)
  },

  getMessageTrace: (messageId) => {
    return apiClient.get(`/api/v1/agent/industry-qa/messages/${encodeURIComponent(messageId)}/trace`)
  }
}

export default industryQaApi
