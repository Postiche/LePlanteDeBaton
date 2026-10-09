import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import EmailComposer from '../components/EmailComposer.jsx'
import { Empty, Field, Loader, Modal, useApi, useToast } from '../components/ui.jsx'
import { VISIT_STATUS, slot } from '../format.js'

export default function Visits() {
  const toast = useToast()
  const { can } = useAuth()
  const [status, setStatus] = useState('proposee,confirmee')
  const [edit, setEdit] = useState(null)
  const [email, setEmail] = useState(null)
  const st = useApi(() => api('/api/visits', { params: { status } }), [status])
  const update = async (v, body) => {
    try { await api(`/api/visits/${v.id}`, { method: 'PATCH', body }); toast('Visite mise à jour'); setEdit(null); st.reload() } catch (e) { toast(e.message, 'error') }
  }
  return (
    <>
      <div className="page-head"><div><h1>Visites</h1><p>Une visite n'est « confirmée » que lorsque vous saisissez le créneau accepté par le client.</p></div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ width: 'auto' }} aria-label="Filtre"><option value="proposee,confirmee">À venir (proposées et confirmées)</option><option value="proposee">Proposées</option><option value="confirmee">Confirmées</option><option value="effectuee">Effectuées</option><option value="annulee">Annulées</option><option value="">Toutes</option></select>
      </div>
      <Loader state={st}>{(list) => !list.length ? <Empty icon="calendar">Aucune visite. Proposez une visite depuis une offre ou une correspondance.</Empty> : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
          {list.map((v) => (
            <article key={v.id} className="card card-body stack" style={{ gap: 8 }}>
              <div className="row"><span className={`badge ${v.status === 'confirmee' ? 'ok' : v.status === 'annulee' ? 'danger' : 'warn'}`}>{VISIT_STATUS[v.status]}</span></div>
              <Link to={`/offres/${v.property.id}`}><h3>{v.property.title || v.property.reference}</h3></Link>
              <div className="small muted">{[v.property.address, v.property.city].filter(Boolean).join(', ')}</div>
              {v.contact && <div className="small">Contact : <Link to={`/contacts/${v.contact.id}`}>{v.contact.display_name}</Link></div>}
              {v.request_label && <div className="small">Demande : {v.request_label}</div>}
              {v.confirmed_slot ? <div><b>Confirmée : {slot(v.confirmed_slot)}</b></div> : (
                <div className="small">Créneaux proposés :<ul style={{ margin: '4px 0', paddingLeft: 18 }}>{(v.proposed_slots || []).map((s) => <li key={s}>{slot(s)}</li>)}{!v.proposed_slots?.length && <li className="muted">aucun (disponibilités demandées)</li>}</ul></div>
              )}
              {v.notes && <div className="small muted">{v.notes}</div>}
              {can('write') && (
                <div className="row">
                  {v.status === 'proposee' && <button className="btn btn-sm btn-primary" onClick={() => setEdit({ v, mode: 'confirm', slot: (v.proposed_slots || [])[0]?.slice(0, 16) || '' })}>Saisir la confirmation</button>}
                  {v.status === 'confirmee' && <button className="btn btn-sm btn-primary" onClick={() => setEdit({ v, mode: 'done', report: '' })}>Visite effectuée</button>}
                  {['proposee', 'confirmee'].includes(v.status) && <button className="btn btn-sm" onClick={() => update(v, { status: 'annulee' })}>Annuler</button>}
                  <button className="btn btn-sm" onClick={() => setEmail({ template: v.status === 'effectuee' ? 'compte_rendu' : 'proposition_visite', property_ids: [v.property.id], contact_id: v.contact?.id, request_id: v.request_id, visit_id: v.id, notes: v.report })}>Email</button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}</Loader>
      {edit?.mode === 'confirm' && (
        <Modal title="Confirmation de la visite" onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Annuler</button><button className="btn btn-primary" disabled={!edit.slot} onClick={() => update(edit.v, { status: 'confirmee', confirmed_slot: edit.slot })}>Enregistrer la confirmation</button></>}>
          <p className="small">Saisissez uniquement un créneau effectivement confirmé par le client.</p>
          <div className="chips mb">{(edit.v.proposed_slots || []).map((s) => <button key={s} className={`chip ${edit.slot === s.slice(0, 16) ? 'on' : ''}`} onClick={() => setEdit({ ...edit, slot: s.slice(0, 16) })}>{slot(s)}</button>)}</div>
          <Field label="Créneau confirmé"><input type="datetime-local" value={edit.slot} onChange={(e) => setEdit({ ...edit, slot: e.target.value })} /></Field>
        </Modal>
      )}
      {edit?.mode === 'done' && (
        <Modal title="Compte rendu de visite" onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Annuler</button><button className="btn btn-primary" onClick={() => update(edit.v, { status: 'effectuee', report: edit.report })}>Enregistrer</button></>}>
          <Field label="Compte rendu"><textarea value={edit.report} onChange={(e) => setEdit({ ...edit, report: e.target.value })} style={{ minHeight: 160 }} /></Field>
        </Modal>
      )}
      {email && <EmailComposer context={email} onClose={() => setEmail(null)} />}
    </>
  )
}
