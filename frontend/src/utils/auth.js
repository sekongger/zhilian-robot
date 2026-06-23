const AUTH_KEY = 'zl_auth'
const AUTH_COOKIE_KEY = 'zl_auth_shared'
const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 7

function parseAuth(raw) {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function getStorage() {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

function getCookieDomain() {
  if (typeof window === 'undefined') return ''
  const host = String(window.location.hostname || '').trim().toLowerCase()
  if (!host || host === 'localhost' || /^[\d.]+$/.test(host)) return ''
  if (host === 'quant-chi.com' || host.endsWith('.quant-chi.com')) {
    return '.quant-chi.com'
  }
  return ''
}

function buildCookieString(value, maxAge = AUTH_COOKIE_MAX_AGE) {
  const parts = [
    `${AUTH_COOKIE_KEY}=${encodeURIComponent(value)}`,
    'Path=/',
    `Max-Age=${maxAge}`,
    'SameSite=Lax',
  ]
  const domain = getCookieDomain()
  if (domain) {
    parts.push(`Domain=${domain}`)
  }
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    parts.push('Secure')
  }
  return parts.join('; ')
}

function readAuthCookie() {
  if (typeof document === 'undefined') return null
  const match = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${AUTH_COOKIE_KEY}=`))
  if (!match) return null
  return parseAuth(decodeURIComponent(match.slice(AUTH_COOKIE_KEY.length + 1)))
}

function writeAuthCookie(payload) {
  if (typeof document === 'undefined' || !payload) return
  document.cookie = buildCookieString(JSON.stringify(payload))
}

function clearAuthCookie() {
  if (typeof document === 'undefined') return
  document.cookie = buildCookieString('', 0)
  document.cookie = `${AUTH_COOKIE_KEY}=; Path=/; Max-Age=0; SameSite=Lax`
}

export const persistAuth = (payload) => {
  if (!payload) return null
  const storage = getStorage()
  if (storage) {
    storage.setItem(AUTH_KEY, JSON.stringify(payload))
  }
  writeAuthCookie(payload)
  return payload
}

export const getAuth = () => {
  const storage = getStorage()
  const localPayload = parseAuth(storage?.getItem(AUTH_KEY))
  if (localPayload) {
    writeAuthCookie(localPayload)
    return localPayload
  }

  const cookiePayload = readAuthCookie()
  if (cookiePayload) {
    if (storage) {
      storage.setItem(AUTH_KEY, JSON.stringify(cookiePayload))
    }
    return cookiePayload
  }

  return null
}

export const isAuthenticated = () => !!getAuth()

export const login = (username, password) => {
  if (username === 'admin' && password === 'quantchi123') {
    persistAuth({ user: 'admin', loggedInAt: new Date().toISOString() })
    return true
  }
  return false
}

export const logout = () => {
  const storage = getStorage()
  storage?.removeItem(AUTH_KEY)
  clearAuthCookie()
}
