import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, download } from '../api.js'
import { QuickContact } from '../components/ContactSelect.jsx'
import Icon from '../components/Icon.jsx'
import { DemoBadge, Empty, Loader, useApi } from '../components/ui.jsx'
import { CONTACT_KINDS, telHref } from '../format.js'

export default function Contacts() {
  const nav = useNavigate()
  const [q, setQ] = useState('')
  const [kind, setKind] = useState('')
  const [creating, setCreating] = useState(false)
  const st = useApi(() => api('/api/contacts', { params: { q, kind } }), [q, kind])
  return (
    <>
      <div className="page-head">
        <div><h1>Contacts</h1><p>Clients, propriétaires, agences, commerciaux et partenaires.</p></div>
        <div className="row">
          <button className="btn" onClick={() => download('/api/exports/contacts.xlsx')}><Icon name="download" />Excel</button>
          <button className="btn btn-accent" onClick={() => setCreating(true)}><Icon name="plus" />Nouveau contact</button>
        </div>
      </div>
      <div className="card card-body mb row">
        <input type="search" placeholder="Nom, email, téléphone…" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 200 }} />
        <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: 'auto' }} aria-label="Catégorie"><option value="">Toutes catégories</option>{Object.entries(CONTACT_KINDS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
      </div>
      <Loader state={st}>{(list) => !list.length ? <Empty icon="users">Aucun contact.</Empty> : (
        <div className="card table-wrap"><table className="table">
          <thead><tr><th>Nom</th><th>Catégorie</th><th className="hide-sm">Société</th><th>Téléphone</th><th className="hide-sm">Email</th></tr></thead>
          <tbody>{list.map((c) => (
            <tr key={c.id} className="clickable" onClick={() => nav(`/contacts/${c.id}`)}>
              <td><b>{c.display_name || '—'}</b> <DemoBadge show={c.is_demo} />{c.opposed_to_prospecting && <span className="badge danger" style={{ marginLeft: 4 }}>Opposé prospection</span>}<div className="small muted">{c.job_title}</div></td>
              <td><span className="badge">{CONTACT_KINDS[c.kind]}</span></td>
              <td className="hide-sm">{c.company_name || '—'}</td>
              <td onClick={(e) => e.stopPropagation()}>{c.phone || c.mobile ? <a href={telHref(c.mobile || c.phone)}>{c.mobile || c.phone}</a> : '—'}</td>
              <td className="hide-sm">{c.email || '—'}</td>
            </tr>))}
          </tbody>
        </table></div>
      )}</Loader>
      {creating && <QuickContact onClose={() => setCreating(false)} onCreated={(c) => nav(`/contacts/${c.id}`)} />}
    </>
  )
}
