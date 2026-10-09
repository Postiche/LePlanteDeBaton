import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import Icon from '../components/Icon.jsx'
import { DemoBadge, Empty, Field, Loader, Modal, useApi, useToast } from '../components/ui.jsx'
import { COMPANY_KINDS } from '../format.js'

const EMPTY = { name: '', kind: 'client', siren: '', address: '', postal_code: '', city: '', phone: '', email: '', website: '', notes: '' }

export default function Companies() {
  const toast = useToast()
  const { can } = useAuth()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [edit, setEdit] = useState(null)
  const [open, setOpen] = useState(null)
  const st = useApi(() => api('/api/companies', { params: { q, kind } }), [q, kind])
  const save = async () => {
    const body = Object.fromEntries(Object.entries(edit).filter(([k]) => k in EMPTY).map(([k, v]) => [k, v === '' ? null : v]))
    try {
      if (edit.id) await api(`/api/companies/${edit.id}`, { method: 'PUT', body })
      else await api('/api/companies', { method: 'POST', body })
      setEdit(null); st.reload(); toast('Entreprise enregistrée')
    } catch (e) { toast(e.message, 'error') }
  }
  return (
    <>
      <div className="page-head"><div><h1>Entreprises</h1><p>Clients, propriétaires, agences et partenaires.</p></div>{can('write') && <button className="btn btn-accent" onClick={() => setEdit({ ...EMPTY })}><Icon name="plus" />Nouvelle entreprise</button>}</div>
      <div className="card card-body mb row">
        <input type="search" placeholder="Nom ou ville" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: 'auto' }} aria-label="Catégorie"><option value="">Toutes</option>{Object.entries(COMPANY_KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
      </div>
      <Loader state={st}>{(list) => !list.length ? <Empty icon="briefcase">Aucune entreprise.</Empty> : (
        <div className="card table-wrap"><table className="table">
          <thead><tr><th>Nom</th><th>Catégorie</th><th className="hide-sm">Ville</th><th className="hide-sm">Téléphone</th><th></th></tr></thead>
          <tbody>{list.map((c) => (
            <tr key={c.id} className="clickable" onClick={async () => setOpen(await api(`/api/companies/${c.id}`))}>
              <td><b>{c.name}</b> <DemoBadge show={c.is_demo} /></td><td><span className="badge">{COMPANY_KINDS[c.kind]}</span></td>
              <td className="hide-sm">{c.city || '—'}</td><td className="hide-sm">{c.phone || '—'}</td>
              <td onClick={(e) => e.stopPropagation()}>{can('write') && <button className="btn btn-sm" onClick={() => setEdit({ ...EMPTY, ...Object.fromEntries(Object.entries(c).map(([k, v]) => [k, v ?? ''])) })}>Modifier</button>}</td>
            </tr>))}
          </tbody>
        </table></div>
      )}</Loader>
      {open && (
        <Modal title={open.name} onClose={() => setOpen(null)}>
          <p className="small muted">{[open.address, open.postal_code, open.city].filter(Boolean).join(' ')} {open.phone && `· ${open.phone}`} {open.email && `· ${open.email}`}</p>
          <h3>Contacts</h3>
          {open.contacts.length ? open.contacts.map((c) => <div key={c.id}><Link to={`/contacts/${c.id}`} onClick={() => setOpen(null)}>{c.display_name}</Link> <span className="muted small">{c.job_title}</span></div>) : <div className="muted small">Aucun.</div>}
          <h3 className="mt">Demandes</h3>
          {open.requests.length ? open.requests.map((r) => <div key={r.id}><Link to={`/demandes/${r.id}`} onClick={() => setOpen(null)}>{r.title || r.reference || `#${r.id}`}</Link></div>) : <div className="muted small">Aucune.</div>}
        </Modal>
      )}
      {edit && (
        <Modal title={edit.id ? 'Modifier l\'entreprise' : 'Nouvelle entreprise'} onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Annuler</button><button className="btn btn-primary" onClick={save}>Enregistrer</button></>}>
          <div className="form-grid">
            <Field label="Nom *"><input type="text" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} required /></Field>
            <Field label="Catégorie"><select value={edit.kind} onChange={(e) => setEdit({ ...edit, kind: e.target.value })}>{Object.entries(COMPANY_KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
            {[['siren', 'SIREN'], ['address', 'Adresse'], ['postal_code', 'Code postal'], ['city', 'Ville'], ['phone', 'Téléphone'], ['email', 'Email'], ['website', 'Site web']].map(([k, l]) => <Field key={k} label={l}><input type="text" value={edit[k]} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} /></Field>)}
            <Field label="Notes" wide><textarea value={edit.notes} onChange={(e) => setEdit({ ...edit, notes: e.target.value })} /></Field>
          </div>
        </Modal>
      )}
    </>
  )
}
