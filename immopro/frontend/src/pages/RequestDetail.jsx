import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, download } from '../api.js'
import { useAuth } from '../auth.jsx'
import ContactCard from '../components/ContactCard.jsx'
import EmailComposer from '../components/EmailComposer.jsx'
import Icon from '../components/Icon.jsx'
import MapView from '../components/MapView.jsx'
import MatchExplain from '../components/MatchExplain.jsx'
import Timeline from '../components/Timeline.jsx'
import VisitModal from '../components/VisitModal.jsx'
import { DemoBadge, Dl, Loader, Modal, Score, useApi, useToast } from '../components/ui.jsx'
import { IMPERATIVES, PIPELINE, PRIORITIES, REQUEST_STATUS, TRANSACTION_LABELS, TYPE_LABELS, date, dateTime, eur, num, priceLabel, propertyLabel } from '../format.js'
import { ExternalSearchPanel } from './External.jsx'

export default function RequestDetail() {
  const { id } = useParams()
  const st = useApi(() => api(`/api/requests/${id}`), [id])
  const [tab, setTab] = useState('biens')
  const [modal, setModal] = useState(null)
  const { can } = useAuth()
  return (
    <Loader state={st}>{(r) => {
      const fallback = !r.contact && (r.contact_name || r.email || r.phone) ? { display_name: r.contact_name, email: r.email, phone: r.phone, company_name: r.client_name } : null
      return (
        <>
          <div className="page-head">
            <div>
              <div className="row small muted"><Link to="/demandes">Demandes</Link> › {r.reference || `#${r.id}`} <DemoBadge show={r.is_demo} />
                <span className="badge">{REQUEST_STATUS[r.status]}</span><span className={`badge ${['haute', 'urgente'].includes(r.priority) ? 'warn' : ''}`}>Priorité {PRIORITIES[r.priority]?.toLowerCase()}</span></div>
              <h1 style={{ marginTop: 6 }}>{r.title || 'Demande client'}</h1>
              <p>{r.display_client || 'Client non renseigné'}</p>
            </div>
            <div className="row">
              <button className="btn btn-accent" onClick={() => setTab('recherche')}><Icon name="search" />Rechercher des biens</button>
              {can('write') && <Link className="btn" to={`/demandes/${r.id}/modifier`}><Icon name="edit" />Modifier</Link>}
            </div>
          </div>
          <div className="split mb">
            <section className="card card-body">
              <h2 className="mb">Critères</h2>
              <div className="grid g2">
                <Dl rows={[
                  ['Types', (r.property_types || []).map((t) => TYPE_LABELS[t]).join(', ') || 'Tous types'],
                  ['Transaction', TRANSACTION_LABELS[r.transaction] || 'Vente ou location'],
                  ['Communes', (r.cities || []).join(', ')], ['Codes postaux', (r.postal_codes || []).join(', ')],
                  ['Départements', (r.departments || []).join(', ')], ['Régions', (r.regions || []).join(', ')],
                  ['Rayon', r.radius_km && r.center_label ? `${r.radius_km} km autour de ${r.center_label}` : null],
                ]} />
                <Dl rows={[
                  ['Surface', r.surface_min || r.surface_max ? `${num(r.surface_min)} à ${num(r.surface_max)} m²` : null],
                  ['Budget max', r.budget_max && eur(r.budget_max)], ['Budget max /m²', r.budget_per_sqm_max && `${num(r.budget_per_sqm_max)} €`],
                  ['Hauteur libre min', r.min_clear_height && num(r.min_clear_height, 'm')], ['Quais min', r.min_docks],
                  ['Accès PL', r.requires_hgv_access ? 'Exigé' : null], ['Puissance min', r.min_power_kva && num(r.min_power_kva, 'kVA')],
                  ['Disponibilité souhaitée', r.desired_date && date(r.desired_date)],
                ]} />
              </div>
              <div className="row mt"><b className="small">Critères impératifs :</b> {(r.imperatives || []).length ? r.imperatives.map((k) => <span key={k} className="badge danger">{IMPERATIVES[k]}</span>) : <span className="small muted">aucun (tous les critères sont souhaitables)</span>}</div>
              {r.other_constraints && <p className="small"><b>Autres contraintes :</b> {r.other_constraints}</p>}
              {r.comments && <p className="small" style={{ whiteSpace: 'pre-wrap' }}><b>Commentaires :</b> {r.comments}</p>}
              <p className="small muted">Créée le {dateTime(r.created_at)} · origine : {r.source_name || r.source_kind}</p>
            </section>
            <div className="stack">
              <ContactCard title="Client" contact={r.contact} fallback={fallback} onEmail={() => setModal({ type: 'email', ctx: { template: 'relance', request_id: r.id } })} />
              {r.center_latitude != null && r.radius_km && <MapView small points={[]} circles={[{ lat: r.center_latitude, lon: r.center_longitude, radius_km: r.radius_km, label: r.center_label }]} />}
            </div>
          </div>
          <div className="tabs">
            {[['biens', 'Biens correspondants'], ['recherche', 'Recherche multisource'], ['historique', 'Historique']].map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}
          </div>
          {tab === 'biens' && <RequestMatches request={r} setModal={setModal} />}
          {tab === 'recherche' && <ExternalSearchPanel request={r} setModal={setModal} />}
          {tab === 'historique' && <section className="card card-body"><Timeline params={{ request_id: r.id }} link={{ request_id: r.id, contact_id: r.contact_id }} /></section>}
          {modal?.type === 'email' && <EmailComposer context={modal.ctx} onClose={() => setModal(null)} />}
          {modal?.type === 'visit' && <VisitModal propertyId={modal.propertyId} requestId={r.id} contactId={r.contact_id} matchId={modal.matchId} onClose={() => setModal(null)} />}
          {modal?.type === 'explain' && <Modal title={`Score ${modal.result.score}/100`} onClose={() => setModal(null)}><MatchExplain result={modal.result} /></Modal>}
        </>
      )
    }}</Loader>
  )
}

export function MatchList({ list, request, setModal, selectable, selected, setSelected, onStatus }) {
  if (!list.length) return <div className="empty">Aucun bien interne compatible.</div>
  return list.map((m) => {
    const p = m.property
    return (
      <article key={p.id} className="card card-body" style={m.eliminated ? { opacity: 0.65 } : null}>
        <div className="row" style={{ alignItems: 'flex-start' }}>
          {selectable && <input type="checkbox" aria-label="Sélectionner" checked={selected.includes(p.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, p.id] : selected.filter((x) => x !== p.id))} style={{ width: 20, height: 20, marginTop: 14 }} />}
          <Score value={m.score} />
          <div style={{ flex: 1, minWidth: 220 }}>
            <div className="row"><span className="badge teal">Base interne</span><DemoBadge show={p.is_demo} />{m.status && <span className="badge navy">{PIPELINE[m.status]}</span>}</div>
            <Link to={`/offres/${p.id}`}><h3 style={{ marginTop: 4 }}>{propertyLabel(p)}</h3></Link>
            <div className="small muted">{[p.reference, [p.postal_code, p.city].filter(Boolean).join(' '), num(p.surface_total, 'm²'), priceLabel(p)].filter(Boolean).join(' · ')}</div>
            {m.eliminated && <div className="badge danger mt">Éliminé : {m.eliminated_by[0]}</div>}
            <div className="small mt"><span style={{ color: 'var(--ok)' }}>✓</span> {m.satisfied.slice(0, 4).join(' · ') || '—'}</div>
            {m.gaps.length > 0 && <div className="small" style={{ color: 'var(--warn)' }}>Écarts : {m.gaps.slice(0, 3).join(' · ')}</div>}
            {m.missing.length > 0 && <div className="small muted">À vérifier : {m.missing.slice(0, 3).join(' · ')}</div>}
          </div>
          <div className="row">
            <button className="btn btn-sm" onClick={() => setModal({ type: 'explain', result: m })}>Détail du score</button>
            <button className="btn btn-sm" onClick={() => setModal({ type: 'email', ctx: { template: 'presentation_bien', property_ids: [p.id], request_id: request.id, match_id: m.match_id } })}><Icon name="mail" />Email</button>
            <button className="btn btn-sm" onClick={() => setModal({ type: 'visit', propertyId: p.id, matchId: m.match_id })}><Icon name="calendar" />Visite</button>
            {onStatus && <select className="btn-sm" style={{ width: 'auto', minHeight: 32 }} value={m.status || ''} onChange={(e) => onStatus(m, e.target.value)} aria-label="Statut commercial">
              <option value="">Statut…</option>{Object.entries(PIPELINE).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select>}
          </div>
        </div>
        {(p.sales_contact || p.agency_contact) && (
          <div className="grid g2 mt">
            {p.sales_contact && <ContactCard title="Commercial" contact={p.sales_contact} />}
            {p.agency_contact && p.agency_contact.id !== p.sales_contact?.id && <ContactCard title="Agence" contact={p.agency_contact} />}
          </div>
        )}
      </article>
    )
  })
}

function RequestMatches({ request, setModal }) {
  const toast = useToast()
  const [elim, setElim] = useState(false)
  const [selected, setSelected] = useState([])
  const st = useApi(() => api(`/api/requests/${request.id}/matches`, { params: { include_eliminated: elim } }), [request.id, elim])
  const onStatus = async (m, status) => {
    if (!status) return
    try {
      const rec = m.match_id ? { id: m.match_id } : await api('/api/matches/ensure', { method: 'POST', body: { request_id: request.id, property_id: m.property.id } })
      await api(`/api/matches/${rec.id}`, { method: 'PATCH', body: { status } })
      toast('Statut mis à jour')
      st.reload()
    } catch (e) { toast(e.message, 'error') }
  }
  return (
    <div className="stack">
      <div className="row">
        <span className="small muted">Calcul en direct sur toutes les offres actives{st.data ? ` · ${st.data.length} bien(s)` : ''}.</span>
        <div className="spacer" />
        <label className="check"><input type="checkbox" checked={elim} onChange={(e) => setElim(e.target.checked)} />Afficher les biens éliminés</label>
      </div>
      {selected.length > 0 && (
        <div className="card card-body row" style={{ position: 'sticky', top: 64, zIndex: 5 }}>
          <b>{selected.length} bien(s) sélectionné(s)</b><div className="spacer" />
          <button className="btn btn-sm" onClick={() => setModal({ type: 'email', ctx: { template: 'selection_biens', property_ids: selected, request_id: request.id } })}><Icon name="mail" />Email de sélection</button>
          <button className="btn btn-sm" onClick={() => download('/api/pdf/dossier', { method: 'POST', body: { property_ids: selected, request_id: request.id } }).catch((e) => toast(e.message, 'error'))}><Icon name="file" />Dossier PDF</button>
          <button className="btn btn-sm btn-ghost" onClick={() => setSelected([])}>Vider</button>
        </div>
      )}
      <Loader state={st}>{(list) => <MatchList list={list} request={request} setModal={setModal} selectable selected={selected} setSelected={setSelected} onStatus={onStatus} />}</Loader>
    </div>
  )
}
