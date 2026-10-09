import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import ContactCard from '../components/ContactCard.jsx'
import Documents from '../components/Documents.jsx'
import EmailComposer from '../components/EmailComposer.jsx'
import Timeline from '../components/Timeline.jsx'
import { Field, Loader, Modal, useApi, useToast } from '../components/ui.jsx'
import { CONTACT_KINDS, REQUEST_STATUS } from '../format.js'

export default function ContactDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const { can } = useAuth()
  const st = useApi(() => api(`/api/contacts/${id}`), [id])
  const docs = useApi(() => api('/api/documents', { params: { owner_type: 'contact', owner_id: id } }), [id])
  const companies = useApi(() => api('/api/companies'), [])
  const [edit, setEdit] = useState(null)
  const [email, setEmail] = useState(false)
  const save = async () => {
    const body = Object.fromEntries(Object.entries(edit).map(([k, v]) => [k, v === '' ? null : v]))
    body.opposed_to_prospecting = !!edit.opposed_to_prospecting
    try { await api(`/api/contacts/${id}`, { method: 'PUT', body }); setEdit(null); st.reload(); toast('Contact enregistré') } catch (e) { toast(e.message, 'error') }
  }
  const exportData = async () => {
    try {
      const data = await api(`/api/contacts/${id}/export`)
      const a = document.createElement('a')
      a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      a.download = `contact-${id}-rgpd.json`
      a.click()
    } catch (e) { toast(e.message, 'error') }
  }
  const erase = async (mode) => {
    if (!window.confirm(mode === 'supprimer' ? 'Supprimer définitivement ce contact ?' : 'Anonymiser ce contact (irréversible) ?')) return
    try { await api(`/api/contacts/${id}`, { method: 'DELETE', params: { mode } }); toast('Demande RGPD traitée'); mode === 'supprimer' ? nav('/contacts') : st.reload() } catch (e) { toast(e.message, 'error') }
  }
  return (
    <Loader state={st}>{(c) => (
      <>
        <div className="page-head">
          <div><div className="small muted"><Link to="/contacts">Contacts</Link> › {CONTACT_KINDS[c.kind]}</div><h1 style={{ marginTop: 6 }}>{c.display_name}</h1><p>{[c.job_title, c.company_name].filter(Boolean).join(' · ')}</p></div>
          {can('write') && <button className="btn" onClick={() => setEdit({ kind: c.kind, civility: c.civility || '', first_name: c.first_name || '', last_name: c.last_name || '', company_id: c.company_id || '', job_title: c.job_title || '', email: c.email || '', phone: c.phone || '', mobile: c.mobile || '', address: c.address || '', origin: c.origin || '', legal_basis: c.legal_basis || '', opposed_to_prospecting: c.opposed_to_prospecting, notes: c.notes || '' })}>Modifier</button>}
        </div>
        <div className="split">
          <div className="stack">
            <section className="card card-body"><h2 className="mb">Historique commercial</h2><Timeline params={{ contact_id: c.id }} link={{ contact_id: c.id, company_id: c.company_id }} /></section>
            <section className="card card-body"><h2 className="mb">Documents</h2><Loader state={docs}>{(d) => <Documents ownerType="contact" ownerId={c.id} documents={d} onChange={docs.reload} />}</Loader></section>
          </div>
          <div className="stack">
            <ContactCard contact={c} onEmail={() => setEmail(true)} />
            {c.notes && <section className="card card-body small"><b>Notes</b><div style={{ whiteSpace: 'pre-wrap' }}>{c.notes}</div></section>}
            <section className="card card-body small">
              <h3 className="mb">Recherches</h3>
              {c.requests.length ? c.requests.map((r) => <div key={r.id}><Link to={`/demandes/${r.id}`}>{r.title || r.reference || `#${r.id}`}</Link> <span className="badge">{REQUEST_STATUS[r.status]}</span></div>) : <span className="muted">Aucune.</span>}
              <h3 className="mb mt">Biens liés</h3>
              {c.properties.length ? c.properties.map((p) => <div key={p.id + p.role}><Link to={`/offres/${p.id}`}>{p.title || p.reference}</Link> <span className="muted">({p.role})</span></div>) : <span className="muted">Aucun.</span>}
            </section>
            {can('admin') && (
              <section className="card card-body small stack" style={{ gap: 8 }}>
                <h3>RGPD</h3>
                <div className="muted">Base légale : {c.legal_basis || 'non renseignée'} · Origine : {c.origin || 'non renseignée'}</div>
                <div className="row"><button className="btn btn-sm" onClick={exportData}>Exporter ses données</button><button className="btn btn-sm" onClick={() => erase('anonymiser')}>Anonymiser</button><button className="btn btn-sm btn-danger" onClick={() => erase('supprimer')}>Supprimer</button></div>
              </section>
            )}
          </div>
        </div>
        {email && <EmailComposer context={{ template: 'relance', contact_id: c.id }} onClose={() => setEmail(false)} />}
        {edit && (
          <Modal title="Modifier le contact" onClose={() => setEdit(null)} footer={<><button className="btn" onClick={() => setEdit(null)}>Annuler</button><button className="btn btn-primary" onClick={save}>Enregistrer</button></>}>
            <div className="form-grid">
              <Field label="Catégorie"><select value={edit.kind} onChange={(e) => setEdit({ ...edit, kind: e.target.value })}>{Object.entries(CONTACT_KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
              <Field label="Civilité"><select value={edit.civility} onChange={(e) => setEdit({ ...edit, civility: e.target.value })}><option value="">—</option><option>M.</option><option>Mme</option></select></Field>
              {[['first_name', 'Prénom'], ['last_name', 'Nom'], ['job_title', 'Fonction'], ['email', 'Email'], ['phone', 'Téléphone'], ['mobile', 'Mobile'], ['address', 'Adresse'], ['origin', 'Origine du contact']].map(([k, l]) => (
                <Field key={k} label={l}><input type="text" value={edit[k]} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} /></Field>
              ))}
              <Field label="Entreprise"><select value={edit.company_id} onChange={(e) => setEdit({ ...edit, company_id: e.target.value ? +e.target.value : '' })}><option value="">—</option>{(companies.data || []).map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></Field>
              <Field label="Base légale"><select value={edit.legal_basis} onChange={(e) => setEdit({ ...edit, legal_basis: e.target.value })}><option value="">—</option><option value="interet_legitime">Intérêt légitime</option><option value="contrat">Contrat / mesures précontractuelles</option><option value="consentement">Consentement</option></select></Field>
              <label className="check wide"><input type="checkbox" checked={!!edit.opposed_to_prospecting} onChange={(e) => setEdit({ ...edit, opposed_to_prospecting: e.target.checked })} />S'oppose à la prospection commerciale</label>
              <Field label="Notes" wide><textarea value={edit.notes} onChange={(e) => setEdit({ ...edit, notes: e.target.value })} /></Field>
            </div>
          </Modal>
        )}
      </>
    )}</Loader>
  )
}
