import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import EmailComposer from '../components/EmailComposer.jsx'
import MatchExplain from '../components/MatchExplain.jsx'
import VisitModal from '../components/VisitModal.jsx'
import { DemoBadge, Empty, Loader, Modal, Score, useApi, useToast } from '../components/ui.jsx'
import { PIPELINE, num } from '../format.js'

export default function Matches() {
  const [sp, setSp] = useSearchParams()
  const toast = useToast()
  const [view, setView] = useState('pipeline')
  const [modal, setModal] = useState(null)
  const status = sp.get('status') || ''
  const minScore = sp.get('min_score') || ''
  const st = useApi(() => api('/api/matches', { params: { status: view === 'list' ? status : '', min_score: minScore, page_size: 500 } }), [status, minScore, view])
  const update = async (m, s) => {
    try { await api(`/api/matches/${m.id}`, { method: 'PATCH', body: { status: s } }); st.reload() } catch (e) { toast(e.message, 'error') }
  }
  const dismiss = async (m) => { try { await api(`/api/matches/${m.id}`, { method: 'PATCH', body: { dismissed: true, note: 'Correspondance écartée' } }); st.reload() } catch (e) { toast(e.message, 'error') } }
  const setF = (k, v) => { const n = new URLSearchParams(sp); if (!v) n.delete(k); else n.set(k, v); setSp(n, { replace: true }) }
  const Item = ({ m }) => (
    <div className="item" onClick={() => setModal({ type: 'explain', m })}>
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <Score value={m.score} small />
        <div style={{ minWidth: 0 }}>
          <b style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.property.title || m.property.reference}</b>
          <div className="small muted">{m.property.city} · {num(m.property.surface_total, 'm²')}</div>
        </div>
      </div>
      <div className="small mt">pour <b>{m.request.client_name || m.request.title}</b> <DemoBadge show={m.property.is_demo} /></div>
    </div>
  )
  return (
    <>
      <div className="page-head">
        <div><h1>Correspondances</h1><p>Offres ↔ demandes au-dessus du seuil configuré, avec suivi commercial.</p></div>
        <div className="row">
          <select value={minScore} onChange={(e) => setF('min_score', e.target.value)} style={{ width: 'auto' }} aria-label="Score minimum"><option value="">Tous scores</option><option value="60">≥ 60</option><option value="75">≥ 75</option><option value="90">≥ 90</option></select>
          <button className={`btn btn-sm ${view === 'pipeline' ? 'btn-primary' : ''}`} onClick={() => setView('pipeline')}>Pipeline</button>
          <button className={`btn btn-sm ${view === 'list' ? 'btn-primary' : ''}`} onClick={() => setView('list')}>Liste</button>
        </div>
      </div>
      <Loader state={st}>{(d) => !d.items.length ? <Empty icon="link">Aucune correspondance. Ajoutez des offres et des demandes : le calcul est automatique.</Empty> : view === 'pipeline' ? (
        <div className="pipeline">
          {Object.entries(PIPELINE).map(([k, l]) => {
            const items = d.items.filter((m) => m.status === k)
            return <div key={k} className="lane"><h3><span>{l}</span><span>{items.length}</span></h3>{items.map((m) => <Item key={m.id} m={m} />)}</div>
          })}
        </div>
      ) : (
        <div className="card table-wrap">
          <div className="card-body"><select value={status} onChange={(e) => setF('status', e.target.value)} style={{ maxWidth: 260 }}><option value="">Tous statuts</option>{Object.entries(PIPELINE).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
          <table className="table">
            <thead><tr><th>Score</th><th>Offre</th><th>Demande</th><th>Statut</th><th></th></tr></thead>
            <tbody>{d.items.map((m) => (
              <tr key={m.id}>
                <td><Score value={m.score} small /></td>
                <td><Link to={`/offres/${m.property.id}`}>{m.property.title || m.property.reference}</Link><div className="small muted">{m.property.city}</div></td>
                <td><Link to={`/demandes/${m.request.id}`}>{m.request.title || m.request.client_name}</Link><div className="small muted">{m.request.client_name}</div></td>
                <td><select value={m.status} onChange={(e) => update(m, e.target.value)} aria-label="Statut">{Object.entries(PIPELINE).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></td>
                <td className="nowrap"><button className="btn btn-sm" onClick={() => setModal({ type: 'explain', m })}>Ouvrir</button></td>
              </tr>))}
            </tbody>
          </table>
        </div>
      )}</Loader>
      {modal?.type === 'explain' && (
        <Modal title={`${modal.m.property.title || modal.m.property.reference} → ${modal.m.request.client_name || modal.m.request.title}`} onClose={() => setModal(null)} footer={<>
          <button className="btn btn-danger" onClick={() => { dismiss(modal.m); setModal(null) }}>Écarter</button>
          <select value={modal.m.status} onChange={(e) => { update(modal.m, e.target.value); setModal(null) }} style={{ width: 'auto' }} aria-label="Statut">{Object.entries(PIPELINE).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          <button className="btn" onClick={() => setModal({ type: 'visit', m: modal.m })}>Proposer une visite</button>
          <button className="btn btn-primary" onClick={() => setModal({ type: 'email', m: modal.m })}>Préparer un email</button>
        </>}>
          <div className="row mb"><Score value={modal.m.score} /><div><Link to={`/offres/${modal.m.property.id}`}>Fiche offre</Link> · <Link to={`/demandes/${modal.m.request.id}`}>Fiche demande</Link><div className="small muted">Calculé le {new Date(modal.m.computed_at).toLocaleString('fr-FR')}</div></div></div>
          <MatchExplain result={modal.m.details} />
        </Modal>
      )}
      {modal?.type === 'email' && <EmailComposer context={{ template: 'presentation_bien', match_id: modal.m.id }} onClose={() => { setModal(null); st.reload() }} />}
      {modal?.type === 'visit' && <VisitModal propertyId={modal.m.property.id} requestId={modal.m.request.id} matchId={modal.m.id} onClose={() => { setModal(null); st.reload() }} />}
    </>
  )
}
