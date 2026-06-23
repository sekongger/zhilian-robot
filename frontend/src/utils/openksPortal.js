export const OPENKS_PORTAL_FALLBACK_BASE_URL = 'https://ai-openks.quant-chi.com'

export function getOpenksPortalUrl(path = '/openks') {
  const configured = String((import.meta.env || {}).VITE_OPENKS_PORTAL_URL || '').trim()
  const base = (configured || OPENKS_PORTAL_FALLBACK_BASE_URL).replace(/\/$/, '')
  if (!path || path === '/') {
    return base
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export default getOpenksPortalUrl
