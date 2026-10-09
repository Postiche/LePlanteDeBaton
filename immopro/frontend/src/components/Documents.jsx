import { useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import Icon from './Icon.jsx'
import { useToast } from './ui.jsx'

// Photos et documents protégés : servis uniquement via /api/files (session requise).
export default function Documents({ ownerType, ownerId, documents = [], onChange }) {
  const toast = useToast()
  const { can } = useAuth()
  const [busy, setBusy] = useState(false)
  const upload = async (files) => {
    setBusy(true)
    for (const f of files) {
      const form = new FormData()
      form.append('owner_type', ownerType)
      form.append('owner_id', ownerId)
      form.append('file', f)
      try { await api('/api/documents', { method: 'POST', form }) } catch (e) { toast(`${f.name} : ${e.message}`, 'error') }
    }
    setBusy(false)
    onChange && onChange()
  }
  const remove = async (d) => {
    if (!window.confirm(`Supprimer « ${d.original_name} » ?`)) return
    try { await api(`/api/documents/${d.id}`, { method: 'DELETE' }); onChange && onChange() } catch (e) { toast(e.message, 'error') }
  }
  const photos = documents.filter((d) => d.kind === 'photo')
  const docs = documents.filter((d) => d.kind !== 'photo')
  return (
    <div className="stack">
      {photos.length > 0 && (
        <div className="gallery">
          {photos.map((p) => (
            <figure key={p.id}>
              <a href={`/api/files/${p.id}`} target="_blank" rel="noreferrer"><img src={`/api/files/${p.id}`} alt={p.caption || p.original_name} loading="lazy" /></a>
              {can('write') && <button className="icon-btn" onClick={() => remove(p)} aria-label="Supprimer la photo"><Icon name="trash" size={16} /></button>}
            </figure>
          ))}
        </div>
      )}
      {docs.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {docs.map((d) => (
            <li key={d.id} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
              <Icon name="file" size={18} />
              <a href={`/api/files/${d.id}?download=true`} style={{ flex: 1 }}>{d.original_name}</a>
              <span className="small muted">{Math.round(d.size / 1024)} Ko</span>
              {can('write') && <button className="icon-btn" onClick={() => remove(d)} aria-label="Supprimer"><Icon name="trash" size={16} /></button>}
            </li>
          ))}
        </ul>
      )}
      {can('write') && (
        <label className="dropzone">
          <input type="file" multiple hidden accept="image/*,.pdf,.docx,.xlsx,.csv,.txt" onChange={(e) => upload([...e.target.files])} disabled={busy} />
          <Icon name="camera" size={22} /><div><b>{busy ? 'Envoi en cours…' : 'Ajouter photos ou documents'}</b></div>
          <div className="small muted">Depuis l'ordinateur ou l'appareil photo du téléphone · JPG, PNG, WebP, HEIC, PDF, Word, Excel, CSV · métadonnées GPS des photos supprimées</div>
        </label>
      )}
    </div>
  )
}
