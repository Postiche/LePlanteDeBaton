import { useCallback, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import MapView from '../components/MapView.jsx'
import { Field, Loader, useApi } from '../components/ui.jsx'
import { TYPE_LABELS, num } from '../format.js'

export default function MapPage() {
  const nav = useNavigate()
  const [type, setType] = useState('')
  const [trans, setTrans] = useState('')
  const [minS, setMinS] = useState('')
  const [reqId, setReqId] = useState('')
  const st = useApi(() => api('/api/properties/map'), [])
  const reqs = useApi(() => api('/api/requests', { params: { page_size: 500 } }), [])
  const req = (reqs.data?.items || []).find((r) => String(r.id) === reqId)
  const filter = useCallback((p) => (!type || p.property_type === type) && (!trans || p.transaction === trans || p.transaction === 'vente_ou_location') && (!minS || (p.surface_total || 0) >= +minS), [type, trans, minS])
  const circles = useMemo(() => (req && req.center_latitude != null && req.radius_km ? [{ lat: req.center_latitude, lon: req.center_longitude, radius_km: req.radius_km, label: `${req.title || 'Demande'} — ${req.radius_km} km` }] : []), [req])
  const onSelect = useCallback((id) => nav(`/offres/${id}`), [nav])
  return (
    <>
      <div className="page-head"><div><h1>Carte des offres</h1><p>Leaflet / OpenStreetMap — aucune coordonnée de contact n'est affichée sur la carte.</p></div></div>
      <div className="card card-body mb">
        <div className="form-grid">
          <Field label="Type"><select value={type} onChange={(e) => setType(e.target.value)}><option value="">Tous</option>{Object.entries(TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Transaction"><select value={trans} onChange={(e) => setTrans(e.target.value)}><option value="">Toutes</option><option value="vente">Vente</option><option value="location">Location</option></select></Field>
          <Field label="Surface min (m²)"><input type="number" value={minS} onChange={(e) => setMinS(e.target.value)} /></Field>
          <Field label="Zone de recherche d'une demande"><select value={reqId} onChange={(e) => setReqId(e.target.value)}><option value="">Aucune</option>{(reqs.data?.items || []).filter((r) => r.radius_km && r.center_latitude != null).map((r) => <option key={r.id} value={r.id}>{r.title || r.reference}</option>)}</select></Field>
        </div>
      </div>
      <Loader state={st}>{(d) => {
        const pts = d.points.filter(filter)
        const ng = d.not_geocoded.filter(filter)
        return (
          <div className="stack">
            <MapView points={pts} circles={circles} onSelect={onSelect} />
            <div className="small muted">{pts.length} offre(s) géolocalisée(s) affichée(s).</div>
            {ng.length > 0 && (
              <section className="card">
                <div className="card-head"><h2>Offres non géocodées ({ng.length})</h2></div>
                <div className="card-body small">
                  <p className="muted" style={{ marginTop: 0 }}>Ces offres n'ont pas de coordonnées : complétez l'adresse ou saisissez la latitude/longitude, ou lancez le géocodage depuis la fiche.</p>
                  {ng.map((p) => <div key={p.id} style={{ padding: '4px 0' }}><Link to={`/offres/${p.id}`}>{p.title || p.reference || `#${p.id}`}</Link> — {[p.address, p.postal_code, p.city].filter(Boolean).join(' ') || 'adresse inconnue'} · {num(p.surface_total, 'm²')}</div>)}
                </div>
              </section>
            )}
          </div>
        )
      }}</Loader>
    </>
  )
}
