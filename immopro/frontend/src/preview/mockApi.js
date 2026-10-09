// Aperçu autonome (sans serveur) : réponses précalculées par le vrai backend sur des données FICTIVES.
// Aucune écriture n'est possible : l'aperçu sert uniquement à découvrir l'interface.
import F from 'preview-fixtures'

let loggedIn = false
const READ_ONLY = "Aperçu de démonstration : l'enregistrement nécessite le serveur ImmoPro."

const norm = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
const has = (obj, q, keys) => keys.some((k) => norm(obj[k]).includes(norm(q)))

function page(items, params, size = 50) {
  const p = +(params.page || 1)
  const ps = +(params.page_size || size)
  return { total: items.length, page: p, page_size: ps, items: items.slice((p - 1) * ps, p * ps) }
}
function demoFilter(items, demo) {
  if (demo === 'real') return items.filter((x) => !x.is_demo)
  if (demo === 'demo') return items.filter((x) => x.is_demo)
  return items
}

function get(path, params) {
  const R = F.routes
  if (path === '/api/auth/me') {
    if (!loggedIn) throw Object.assign(new Error('Authentification requise.'), { status: 401 })
    return R[path]
  }
  if (path === '/api/properties') {
    let it = R[path].items
    const st = params.status || 'actives'
    if (st === 'actives') it = it.filter((p) => ['active', 'sous_offre'].includes(p.status))
    else if (st !== 'toutes') it = it.filter((p) => p.status === st)
    if (params.q) it = it.filter((p) => has(p, params.q, ['reference', 'title', 'city', 'address', 'description', 'postal_code']))
    if (params.property_type) it = it.filter((p) => params.property_type.split(',').includes(p.property_type))
    if (params.transaction) it = it.filter((p) => p.transaction === params.transaction || p.transaction === 'vente_ou_location')
    if (params.city) it = it.filter((p) => has(p, params.city, ['city']))
    if (params.department) it = it.filter((p) => params.department.split(',').map((d) => d.trim().padStart(2, '0')).includes(p.department))
    if (params.surface_min) it = it.filter((p) => (p.surface_total ?? -1) >= +params.surface_min)
    if (params.surface_max) it = it.filter((p) => p.surface_total != null && (p.surface_total <= +params.surface_max || (p.surface_divisible_min ?? Infinity) <= +params.surface_max))
    if (params.price_max) it = it.filter((p) => p.sale_price != null && p.sale_price <= +params.price_max)
    if (params.rent_max) it = it.filter((p) => p.annual_rent != null && p.annual_rent <= +params.rent_max)
    if (params.min_height) it = it.filter((p) => (p.clear_height ?? -1) >= +params.min_height)
    if (params.min_docks) it = it.filter((p) => (p.dock_count ?? -1) >= +params.min_docks)
    if (params.hgv) it = it.filter((p) => p.hgv_access === (params.hgv === 'true'))
    if (params.geocoded) it = it.filter((p) => (p.latitude != null) === (params.geocoded === 'true'))
    if (params.source_kind) it = it.filter((p) => p.source_kind === params.source_kind)
    it = demoFilter(it, params.demo)
    if (params.sort) {
      const k = params.sort.replace('-', '')
      const dir = params.sort.startsWith('-') ? -1 : 1
      it = [...it].sort((a, b) => ((a[k] ?? Infinity) > (b[k] ?? Infinity) ? dir : -dir))
    }
    return page(it, params, 48)
  }
  if (path === '/api/requests') {
    let it = R[path].items
    const st = params.status || 'active'
    if (st !== 'toutes') it = it.filter((r) => r.status === st)
    if (params.q) it = it.filter((r) => has(r, params.q, ['reference', 'title', 'client_name', 'contact_name', 'email', 'comments']))
    if (params.priority) it = it.filter((r) => r.priority === params.priority)
    if (params.transaction) it = it.filter((r) => r.transaction === params.transaction)
    if (params.property_type) it = it.filter((r) => (r.property_types || []).includes(params.property_type))
    if (params.department) it = it.filter((r) => (r.departments || []).includes(params.department.padStart(2, '0')))
    return page(demoFilter(it, params.demo), params, 200)
  }
  if (path === '/api/matches') {
    let it = R[path].items
    if (params.status) it = it.filter((m) => params.status.split(',').includes(m.status))
    if (params.min_score) it = it.filter((m) => m.score >= +params.min_score)
    return { ...R[path], total: it.length, items: it }
  }
  if (path === '/api/contacts') {
    let it = R[path]
    if (params.q) it = it.filter((c) => has(c, params.q, ['first_name', 'last_name', 'email', 'phone', 'mobile']))
    if (params.kind) it = it.filter((c) => c.kind === params.kind)
    return it
  }
  if (path === '/api/companies') {
    let it = R[path]
    if (params.q) it = it.filter((c) => has(c, params.q, ['name', 'city']))
    if (params.kind) it = it.filter((c) => c.kind === params.kind)
    return it
  }
  if (path === '/api/visits') return params.status ? R[path].filter((v) => params.status.split(',').includes(v.status)) : R[path]
  if (path === '/api/interactions') return params.reminders ? R['/api/interactions?reminders'] : []
  if (path === '/api/timeline') return R[`/api/timeline?${params.property_id ? 'property_id=' + params.property_id : 'request_id=' + params.request_id}`] || []
  if (path === '/api/documents') return []
  if (path === '/api/external/listings') return params.q ? R[path].filter((l) => has(l, params.q, ['title', 'city'])) : R[path]
  if (path === '/api/external/searches') return []
  if (path === '/api/audit') return R[path]
  const key = path + (params.include_eliminated === true || params.include_eliminated === 'true' ? '#elim' : '')
  if (key in R) return R[key]
  if (path in R) return R[path]
  throw Object.assign(new Error("Contenu non disponible dans l'aperçu."), { status: 404 })
}

function compose(body) {
  let { template, property_ids = [], request_id, contact_id, match_id } = body
  if (match_id && F.match_index[match_id]) {
    const [r, p] = F.match_index[match_id]
    request_id = request_id || r
    if (!property_ids.includes(p)) property_ids = [p, ...property_ids]
  }
  const C = F.compose
  const k = (props, req, ct) => [template, props.join(','), req || '', ct || ''].join('|')
  const out = C[k(property_ids, request_id, contact_id)] || C[k(property_ids, request_id)] || C[k(property_ids.slice(0, 1), request_id)] || C[k(property_ids.slice(0, 1))] || C[k([], request_id)] || C[k([], null, contact_id)] || C[k([])]
  return { ...out, match_id: match_id || null, warnings: [...(out.warnings || []), "Aperçu : texte généré à l'avance sur les données fictives."] }
}

export async function mockApi(path, { method = 'GET', body, params = {} } = {}) {
  await new Promise((r) => setTimeout(r, 60))
  const fail = (status, msg) => { throw Object.assign(new Error(msg), { status, detail: msg }) }
  if (method === 'GET') {
    try { return structuredClone(get(path, params)) } catch (e) { fail(e.status || 404, e.message) }
  }
  if (path === '/api/auth/login') { loggedIn = true; return { user: F.routes['/api/auth/me'].user } }
  if (path === '/api/auth/logout') { loggedIn = false; return { ok: true } }
  if (path === '/api/emails/compose') return structuredClone(compose(body))
  const m = path.match(/^\/api\/external\/search\/(\d+)$/)
  if (m) return structuredClone(F.routes[`POST ${path}`])
  return fail(403, READ_ONLY)
}

export const PREVIEW_READ_ONLY = READ_ONLY
