import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, download } from '../api.js'
import Icon from '../components/Icon.jsx'
import { DemoBadge, Empty, Field, Loader, useApi } from '../components/ui.jsx'
import { PRIORITIES, REQUEST_STATUS, TRANSACTION_LABELS, TYPE_LABELS, eur, num } from '../format.js'

export default function Requests() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const p = Object.fromEntries(['q', 'status', 'priority', 'property_type', 'transaction', 'department', 'demo'].map((k) => [k, sp.get(k) || '']))
  const st = useApi(() => api('/api/requests', { params: { ...p, status: p.status || 'active', page_size: 200 } }), [sp.toString()])
  const setF = (k, v) => { const n = new URLSearchParams(sp); if (!v) n.delete(k); else n.set(k, v); setSp(n, { replace: true }) }
  return (
    <>
      <div className="page-head">
        <div><h1>Demandes clients</h1><p>{st.data ? `${st.data.total} demande(s)` : ''}</p></div>
        <div className="row">
          <button className="btn" onClick={() => download('/api/exports/demandes.xlsx')}><Icon name="download" />Excel</button>
          <Link className="btn btn-accent" to="/demandes/nouvelle"><Icon name="plus" />Nouvelle demande</Link>
        </div>
      </div>
      <div className="card card-body mb">
        <div className="form-grid">
          <Field label="Recherche"><input type="search" value={p.q} onChange={(e) => setF('q', e.target.value)} placeholder="Client, référence, email…" /></Field>
          <Field label="Statut"><select value={p.status} onChange={(e) => setF('status', e.target.value)}>{Object.entries(REQUEST_STATUS).map(([k, l]) => <option key={k} value={k === 'active' ? '' : k}>{l}</option>)}<option value="toutes">Toutes</option></select></Field>
          <Field label="Priorité"><select value={p.priority} onChange={(e) => setF('priority', e.target.value)}><option value="">Toutes</option>{Object.entries(PRIORITIES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Type recherché"><select value={p.property_type} onChange={(e) => setF('property_type', e.target.value)}><option value="">Tous</option>{Object.entries(TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Département"><input type="text" value={p.department} onChange={(e) => setF('department', e.target.value)} /></Field>
          <Field label="Données"><select value={p.demo} onChange={(e) => setF('demo', e.target.value)}><option value="">Toutes</option><option value="real">Réelles</option><option value="demo">Démonstration</option></select></Field>
        </div>
      </div>
      <Loader state={st}>{(d) => !d.items.length ? <Empty icon="search">Aucune demande.</Empty> : (
        <div className="card table-wrap">
          <table className="table">
            <thead><tr><th>Client</th><th>Recherche</th><th className="hide-sm">Localisation</th><th className="right">Surface</th><th className="right hide-sm">Budget</th><th>Priorité</th><th className="right">Biens</th></tr></thead>
            <tbody>{d.items.map((r) => (
              <tr key={r.id} className="clickable" onClick={() => nav(`/demandes/${r.id}`)}>
                <td><b>{r.display_client || '—'}</b> <DemoBadge show={r.is_demo} /><div className="small muted">{r.reference}</div></td>
                <td>{r.title || '—'}<div className="small muted">{(r.property_types || []).map((t) => TYPE_LABELS[t]).join(', ') || 'Tous types'} · {TRANSACTION_LABELS[r.transaction] || 'Vente ou location'}</div></td>
                <td className="hide-sm small">{[...(r.cities || []), ...(r.departments || []).map((x) => 'Dépt ' + x), ...(r.regions || [])].join(', ') || (r.center_label ? `${r.radius_km} km autour de ${r.center_label}` : '—')}</td>
                <td className="right nowrap">{r.surface_min || r.surface_max ? `${num(r.surface_min)} – ${num(r.surface_max)} m²` : '—'}</td>
                <td className="right nowrap hide-sm">{r.budget_max ? eur(r.budget_max) : '—'}</td>
                <td><span className={`badge ${r.priority === 'urgente' ? 'danger' : r.priority === 'haute' ? 'warn' : ''}`}>{PRIORITIES[r.priority]}</span></td>
                <td className="right"><span className="badge teal">{r.match_count}</span></td>
              </tr>))}
            </tbody>
          </table>
        </div>
      )}</Loader>
    </>
  )
}
