export function pickGraphPreviewCompany(headlines = []) {
  for (const item of headlines) {
    const companies = Array.isArray(item?.companies) ? item.companies : []
    const first = String(companies[0] || '').trim()
    if (first) return first
  }
  return '华为'
}

export function buildMomentumPreview(entities = []) {
  return (Array.isArray(entities) ? entities : [])
    .slice(0, 5)
    .map((item) => ({
      name: item?.name || '未知',
      percentage: Math.round((Number(item?.current_momentum) || 0) * 100),
    }))
}
