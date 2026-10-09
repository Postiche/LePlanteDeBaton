import { useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { INTERACTION_KINDS, PIPELINE, VISIT_STATUS, dateTime, localToUtc } from '../format.js'
import { Field, useApi, useToast } from './ui.jsx'

const TYPE_LABEL = { interaction: '', visite: 'Visite', email: 'Email' }
const EMAIL_STATUS = { brouillon: 'brouillon', ouvert_messagerie: 'ouvert dans la messagerie (non envoyé)', brouillon_outlook: 'brouillon Outlook (non envoyé)', eml_telecharge: '.eml téléchargé (non envoyé)', envoye_confirme: 'envoi confirmé' }

// Historique chronologique + ajout de notes / rappels.
export default function Timeline({ params, link }) {
  const toast = useToast()
  const { can } = useAuth()
  const url = params.contact_id ? `/api/contacts/${params.contact_id}/timeline` : '/api/timeline'
  const st = useApi(() => api(url, { params: params.contact_id ? undefined : params }), [JSON.stringify(params)])
  const [form, setForm] = useState({ kind: 'note', subject: '', content: '', remind_at: '' })
  const add = async (e) => {
    e.preventDefault()
    try {
      await api('/api/interactions', { method: 'POST', body: { ...link, ...form, remind_at: localToUtc(form.remind_at) } })
      setForm({ kind: 'note', subject: '', content: '', remind_at: '' })
      st.reload()
    } catch (err) { toast(err.message, 'error') }
  }
  return (
    <div className="stack">
      {can('write') && (
        <form onSubmit={add} className="stack" style={{ gap: 10 }}>
          <div className="form-grid">
            <Field label="Type">
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                {['note', 'appel', 'rendez_vous', 'relance', 'compte_rendu'].map((k) => <option key={k} value={k}>{INTERACTION_KINDS[k]}</option>)}
              </select>
            </Field>
            <Field label="Objet"><input type="text" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} required /></Field>
            <Field label="Rappel le (facultatif)"><input type="datetime-local" value={form.remind_at} onChange={(e) => setForm({ ...form, remind_at: e.target.value })} /></Field>
          </div>
          <textarea placeholder="Détails…" value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} style={{ minHeight: 60 }} />
          <div><button className="btn btn-primary btn-sm">Ajouter à l'historique</button></div>
        </form>
      )}
      {st.loading ? <div className="spinner" /> : !st.data?.length ? <div className="muted small">Aucun historique.</div> : (
        <ul className="timeline">
          {st.data.map((i) => (
            <li key={i.type + i.id + i.at}>
              <div className="small muted">{dateTime(i.at)} · {TYPE_LABEL[i.type] || INTERACTION_KINDS[i.kind] || i.kind}
                {i.type === 'visite' && ` · ${VISIT_STATUS[i.kind] || i.kind}`}
                {i.type === 'email' && ` · ${EMAIL_STATUS[i.kind] || i.kind}`}
              </div>
              <div><b>{i.subject || PIPELINE[i.kind]}</b></div>
              {i.content && <div className="small" style={{ whiteSpace: 'pre-wrap' }}>{i.content}</div>}
              {i.remind_at && <span className={`badge ${i.done ? 'ok' : 'warn'}`}>Rappel {dateTime(i.remind_at)}{i.done ? ' · fait' : ''}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
