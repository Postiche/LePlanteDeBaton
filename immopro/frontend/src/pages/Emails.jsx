import { useState } from 'react'
import { api } from '../api.js'
import EmailComposer from '../components/EmailComposer.jsx'
import Icon from '../components/Icon.jsx'
import { Empty, Loader, Modal, useApi } from '../components/ui.jsx'
import { dateTime } from '../format.js'

export default function Emails() {
  const st = useApi(() => api('/api/emails/drafts'), [])
  const [compose, setCompose] = useState(false)
  const [view, setView] = useState(null)
  return (
    <>
      <div className="page-head"><div><h1>Emails préparés</h1><p>Historique des brouillons. Seuls les emails marqués « envoi confirmé » sont considérés comme envoyés.</p></div>
        <button className="btn btn-accent" onClick={() => setCompose(true)}><Icon name="plus" />Nouvel email</button></div>
      <Loader state={st}>{(list) => !list.length ? <Empty icon="mail">Aucun email préparé.</Empty> : (
        <div className="card table-wrap"><table className="table">
          <thead><tr><th>Objet</th><th className="hide-sm">Destinataire</th><th>Statut</th><th className="hide-sm">Modifié</th></tr></thead>
          <tbody>{list.map((d) => (
            <tr key={d.id} className="clickable" onClick={() => setView(d)}>
              <td><b>{d.subject}</b></td><td className="hide-sm">{d.to_email || '—'}</td>
              <td><span className={`badge ${d.status === 'envoye_confirme' ? 'ok' : 'warn'}`}>{d.status_label}</span></td>
              <td className="hide-sm">{dateTime(d.updated_at)}</td>
            </tr>))}
          </tbody>
        </table></div>
      )}</Loader>
      {compose && <EmailComposer context={{ template: 'relance' }} onClose={() => { setCompose(false); st.reload() }} />}
      {view && <Modal title={view.subject} onClose={() => setView(null)}><div className="small muted mb">À : {view.to_email || '—'} · {view.status_label}</div><pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>{view.body}</pre></Modal>}
    </>
  )
}
