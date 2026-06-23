const DEFAULT_GRAPH_QUICK_TAGS = ['华为', '特斯拉', '小米', 'ABB']

export function buildGraphQuickTags({ artifactContext, availableCompanies = [] } = {}) {
  if (artifactContext?.hasArtifactContext && Array.isArray(availableCompanies) && availableCompanies.length > 0) {
    return availableCompanies
  }
  return DEFAULT_GRAPH_QUICK_TAGS
}

export function pickInitialArtifactCompany({ artifactContext, availableCompanies = [], searchName = '' } = {}) {
  if (String(searchName || '').trim()) return String(searchName).trim()
  if (!artifactContext?.hasArtifactContext) return ''
  return String((availableCompanies || [])[0] || '').trim()
}
