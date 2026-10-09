import { useState } from 'react'
import { api } from '../api.js'
import { CONTACT_KINDS } from '../format.js'
import { Modal, useApi, useToast } from './ui.jsx'

export default function ContactSelect({ value, onChange, kind, label }) {
  const st = useApi(() => api('/api/contacts'), [])
  const [creating, setCreating] = useState(false)
  const list = (st.data || []).filter((c) => !kind || c.kind === kind || c.id === value)
  return (
    <label className="field">{label}
      <div className="row" style={{ flexWrap: 'nowrap' }}>
        <select value={value || ''} onChange={(e) => onChange(e.target.value ? +e.target.value : null)}>
          <option value="">— Aucun —</option>
          {list.map((c) => <option key={c.id} value={c.id}>{c.display_name}{c.company_name ? ` (${c.company_name})` : ''}{c.is_demo ? ' [DÉMO]' : ''}</option>)}
        </select>
        <button type="button" className="btn btn-sm" onClick={() => setCreating(true)} title="Nouveau contact">+</button>
      </div>
      {creating && <QuickContact kind={kind} onClose={() => setCreating(false)} onCreated={(c) => { st.reload(); onChange(c.id); setCreating(false) }} />}
    </label>
  )
}

export function QuickContact({ kind = 'client', onClose, onCreated }) {
  const toast = useToast()
  const [f, setF] = useState({ kind, civility: '', first_name: '', last_name: '', job_title: '', email: '', phone: '', origin: '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const save = async () => {
    try { onCreated(await api('/api/contacts', { method: 'POST', body: { ...f, email: f.email || null, civility: f.civility || null } })) } catch (e) { toast(e.message, 'error') }
  }
  return (
    <Modal title="Nouveau contact" onClose={onClose} footer={<><button className="btn" type="button" onClick={onClose}>Annuler</button><button type="button" className="btn btn-primary" onClick={save}>Créer</button></>}>
      <div className="form-grid">
        <label className="field">Catégorie<select value={f.kind} onChange={set('kind')}>{Object.entries(CONTACT_KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
        <label className="field">Civilité<select value={f.civility} onChange={set('civility')}><option value="">—</option><option>M.</option><option>Mme</option></select></label>
        <label className="field">Prénom<input type="text" value={f.first_name} onChange={set('first_name')} /></label>
        <label className="field">Nom<input type="text" value={f.last_name} onChange={set('last_name')} /></label>
        <label className="field">Fonction<input type="text" value={f.job_title} onChange={set('job_title')} /></label>
        <label className="field">Email<input type="email" value={f.email} onChange={set('email')} /></label>
        <label className="field">Téléphone<input type="tel" value={f.phone} onChange={set('phone')} /></label>
        <label className="field wide">Origine du contact (RGPD)<input type="text" value={f.origin} onChange={set('origin')} placeholder="ex. Salon SITL 2026, recommandation, annonce publique…" /></label>
      </div>
    </Modal>
  )
}
