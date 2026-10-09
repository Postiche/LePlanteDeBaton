// Client API : cookies de session HttpOnly (same-origin) + en-tête CSRF sur les écritures.
let csrfToken = null
export function setCsrf(token) { csrfToken = token }

function readCsrfCookie() {
  const m = document.cookie.match(/(?:^|;\s*)(?:__Host-)?immopro_csrf=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : null
}

export class ApiError extends Error {
  constructor(status, detail) {
    const msg = typeof detail === 'string' ? detail : detail?.message || 'Erreur inattendue'
    super(msg)
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, params, raw = false, form } = {}) {
  let url = path
  if (params) {
    const qs = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') qs.append(k, v) })
    const s = qs.toString()
    if (s) url += (url.includes('?') ? '&' : '?') + s
  }
  const headers = {}
  if (method !== 'GET') headers['X-CSRF-Token'] = csrfToken || readCsrfCookie() || ''
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res
  try {
    res = await fetch(url, { method, headers, body: payload, credentials: 'same-origin' })
  } catch {
    throw new ApiError(0, 'Connexion au serveur impossible. Vérifiez votre réseau.')
  }
  if (res.status === 401 && !path.startsWith('/api/auth/')) {
    window.dispatchEvent(new CustomEvent('immopro:unauthorized'))
  }
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail } catch { /* corps non JSON */ }
    throw new ApiError(res.status, detail)
  }
  if (raw) return res
  if (res.status === 204) return null
  return res.json()
}

export async function download(path, { method = 'GET', body, filename } = {}) {
  const res = await api(path, { method, body, raw: true })
  const blob = await res.blob()
  const cd = res.headers.get('content-disposition') || ''
  const m = cd.match(/filename="?([^";]+)"?/)
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename || (m ? m[1] : 'fichier')
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 2000)
}
