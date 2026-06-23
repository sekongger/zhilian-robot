export const PLATFORM_PORTAL_FALLBACK_BASE_URL = 'https://ai-zhilian.quant-chi.com'

export function getPlatformPortalUrl(path = '/platform?tab=knowledge-computing') {
  const configured = String((import.meta.env || {}).VITE_PLATFORM_PORTAL_URL || '').trim()
  const base = (configured || PLATFORM_PORTAL_FALLBACK_BASE_URL).replace(/\/$/, '')
  if (!path || path === '/') {
    return base
  }
  return `${base}${path.startsWith('/') ? path : `/${path}`}`
}

export default getPlatformPortalUrl
