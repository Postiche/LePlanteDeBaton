import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { Empty, Loader, useApi, useToast } from '../components/ui.jsx'
import { INTERACTION_KINDS, dateTime } from '../format.js'

export default function Reminders() {
  const toast = useToast()
  const [dueOnly, setDueOnly] = useState(false)
  const st = useApi(() => api('/api/interactions', { params: { reminders: true, due_only: dueOnly } }), [dueOnly])
  const done = async (i) => { try { await api(`/api/interactions/${i.id}`, { method: 'PATCH', body: { done: true } }); st.reload() } catch (e) { toast(e.message, 'error') } }
  const postpone = async (i, days) => {
    const d = new Date(Math.max(Date.now(), new Date(i.remind_at).getTime()) + days * 86400000)
    try { await api(`/api/interactions/${i.id}`, { method: 'PATCH', body: { remind_at: d.toISOString().slice(0, 19) } }); st.reload() } catch (e) { toast(e.message, 'error') }
  }
  const now = new Date()
  return (
    <>
      <div className="page-head"><div><h1>Relances et rappels</h1><p>Créez un rappel depuis l'historique d'un contact, d'une offre ou d'une demande.</p></div>
        <label className="check"><input type="checkbox" checked={dueOnly} onChange={(e) => setDueOnly(e.target.checked)} />Échéance sous 24 h uniquement</label></div>
      <Loader state={st}>{(list) => !list.length ? <Empty icon="bell">Aucun rappel en attente.</Empty> : (
        <div className="stack">{list.map((i) => {
          const late = new Date(i.remind_at) < now
          return (
            <article key={i.id} className="card card-body row">
              <div style={{ flex: 1, minWidth: 220 }}>
                <div className="row"><span className={`badge ${late ? 'danger' : 'warn'}`}>{late ? 'En retard' : 'À venir'} · {dateTime(i.remind_at)}</span><span className="badge">{INTERACTION_KINDS[i.kind]}</span></div>
                <b>{i.subject}</b>
                {i.content && <div className="small">{i.content}</div>}
                <div className="small muted">
                  {i.contact_id && <Link to={`/contacts/${i.contact_id}`}>{i.contact_name}</Link>}
                  {i.request_id && <> · <Link to={`/demandes/${i.request_id}`}>{i.request_label}</Link></>}
                  {i.property_id && <> · <Link to={`/offres/${i.property_id}`}>{i.property_label}</Link></>}
                </div>
              </div>
              <button className="btn btn-sm" onClick={() => postpone(i, 1)}>+1 jour</button>
              <button className="btn btn-sm" onClick={() => postpone(i, 7)}>+1 semaine</button>
              <button className="btn btn-sm btn-primary" onClick={() => done(i)}>Fait</button>
            </article>
          )
        })}</div>
      )}</Loader>
    </>
  )
}
