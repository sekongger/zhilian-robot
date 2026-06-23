export function buildAssistantPlaceholder(status) {
  switch (String(status || '').trim()) {
    case 'processing':
      return '正在创建问答任务…'
    case 'retrieving':
      return '正在检索 workflow / 图谱数据…'
    case 'answering':
      return '正在生成回答…'
    default:
      return '正在处理中…'
  }
}
