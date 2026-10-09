import { useState } from 'react'
import { api, download } from '../api.js'
import { useAuth } from '../auth.jsx'
import { outlookToken } from '../components/EmailComposer.jsx'
import { Field, Loader, Modal, useApi, useToast } from '../components/ui.jsx'
import { dateTime } from '../format.js'

const WEIGHT_LABELS = { localisation: 'Localisation', surface: 'Surface', budget: 'Budget', typologie: 'Typologie', technique: 'Caractéristiques techniques', disponibilite: 'Disponibilité' }

export default function Settings() {
  const { can } = useAuth()
  const [tab, setTab] = useState('matching')
  const tabs = [['matching', 'Matching'], ['general', 'Général'], ['connecteurs', 'Connecteurs'], ['outlook', 'Outlook'], ['exports', 'Exports']]
  if (can('admin')) tabs.push(['users', 'Utilisateurs'], ['backups', 'Sauvegardes'], ['audit', 'Journal'])
  return (
    <>
      <div className="page-head"><div><h1>Paramètres</h1><p>{can('admin') ? 'Configuration de l\'application.' : 'Consultation (modification réservée aux administrateurs).'}</p></div></div>
      <div className="tabs">{tabs.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>
      {['matching', 'general', 'connecteurs', 'outlook'].includes(tab) && <SettingsForm tab={tab} />}
      {tab === 'exports' && <Exports />}
      {tab === 'users' && <Users />}
      {tab === 'backups' && <Backups />}
      {tab === 'audit' && <Audit />}
    </>
  )
}

function SettingsForm({ tab }) {
  const { can, setSettings } = useAuth()
  const toast = useToast()
  const st = useApi(() => api('/api/settings'), [])
  const [token, setToken] = useState(outlookToken())
  const [agent, setAgent] = useState(null)
  const save = async (patch) => {
    try { const s = await api('/api/settings', { method: 'PUT', body: patch }); st.setData(s); setSettings(s); toast('Paramètres enregistrés') } catch (e) { toast(e.message, 'error') }
  }
  const testAgent = async (url) => {
    try {
      const r = await fetch(`${url.replace(/\/$/, '')}/status`, { headers: { 'X-Agent-Token': token } })
      setAgent(await r.json())
    } catch { setAgent({ ok: false, error: 'Agent injoignable depuis ce navigateur (non lancé, autre poste, ou navigateur bloquant l\'accès local).' }) }
  }
  const ro = !can('admin')
  return (
    <Loader state={st}>{(s) => {
      const set = (k, v) => st.setData({ ...s, [k]: v })
      if (tab === 'matching') {
        const total = Object.values(s.matching_weights).reduce((a, b) => a + Number(b || 0), 0)
        return (
          <section className="card card-body stack" style={{ maxWidth: 720 }}>
            <h2>Pondérations du score</h2>
            <p className="small muted" style={{ margin: 0 }}>Les pondérations sont normalisées sur 100. Toute modification recalcule l'ensemble des correspondances.</p>
            {Object.entries(WEIGHT_LABELS).map(([k, l]) => (
              <div key={k} className="row">
                <span style={{ width: 220 }}>{l}</span>
                <input type="range" min="0" max="60" value={s.matching_weights[k] ?? 0} disabled={ro} onChange={(e) => set('matching_weights', { ...s.matching_weights, [k]: +e.target.value })} style={{ flex: 1, minHeight: 'auto' }} aria-label={l} />
                <b style={{ width: 70, textAlign: 'right' }}>{total ? Math.round(((s.matching_weights[k] || 0) / total) * 100) : 0} %</b>
              </div>
            ))}
            <Field label="Score minimum pour enregistrer une correspondance" hint="Les biens sous ce seuil restent visibles depuis les fiches (calcul en direct)."><input type="number" min="0" max="100" value={s.matching_min_score} disabled={ro} onChange={(e) => set('matching_min_score', e.target.value)} /></Field>
            {!ro && <div className="row"><button className="btn btn-primary" onClick={() => save({ matching_weights: s.matching_weights, matching_min_score: Number(s.matching_min_score) })}>Enregistrer et recalculer</button><button className="btn" onClick={() => set('matching_weights', { localisation: 30, surface: 25, budget: 20, typologie: 10, technique: 10, disponibilite: 5 })}>Valeurs initiales</button></div>}
          </section>
        )
      }
      if (tab === 'general') return (
        <section className="card card-body stack" style={{ maxWidth: 720 }}>
          <Field label="Nom de la société (fiches PDF, signatures)"><input type="text" value={s.company_name || ''} disabled={ro} onChange={(e) => set('company_name', e.target.value)} /></Field>
          <Field label="Durée de fraîcheur des annonces externes (jours)"><input type="number" value={s.external_freshness_days} disabled={ro} onChange={(e) => set('external_freshness_days', e.target.value)} /></Field>
          <Field label="Conservation des contacts inactifs (mois) — rappel RGPD"><input type="number" value={s.retention_months_inactive_contacts} disabled={ro} onChange={(e) => set('retention_months_inactive_contacts', e.target.value)} /></Field>
          <Field label="Fond de carte (URL de tuiles HTTPS)" hint="Par défaut OpenStreetMap : usage modéré, attribution obligatoire. Pour un usage intensif, utilisez un fournisseur de tuiles sous contrat."><input type="url" value={s.map_tile_url} disabled={ro} onChange={(e) => set('map_tile_url', e.target.value)} /></Field>
          <Field label="Attribution de la carte"><input type="text" value={s.map_attribution} disabled={ro} onChange={(e) => set('map_attribution', e.target.value)} /></Field>
          {!ro && <div><button className="btn btn-primary" onClick={() => save({ company_name: s.company_name, external_freshness_days: Number(s.external_freshness_days), retention_months_inactive_contacts: Number(s.retention_months_inactive_contacts), map_tile_url: s.map_tile_url, map_attribution: s.map_attribution })}>Enregistrer</button></div>}
          <div className="small muted">Environnement : {s.app_env}</div>
        </section>
      )
      if (tab === 'connecteurs') return (
        <section className="card card-body stack" style={{ maxWidth: 820 }}>
          <div className="alert warn small">
            <b>État réel des connecteurs :</b> aucune API officielle de BureauxLocaux ou Geolocaux n'est configurée et l'application n'effectue aucune extraction automatique (pas de scraping, pas de contournement de captcha ou de restrictions). Le bouton « Rechercher des biens » ouvre la plateforme et affiche les critères à reporter ; les annonces sont ensuite importées manuellement puis validées.
          </div>
          <p className="small" style={{ margin: 0 }}>Facultatif : si vous avez vous-même vérifié la forme d'une URL de recherche sur la plateforme, enregistrez-la comme modèle. Variables disponibles : <code>{'{ville} {code_postal} {departement} {surface_min} {surface_max} {budget_max} {transaction} {type}'}</code>. Le modèle doit commencer par l'adresse officielle de la plateforme.</p>
          <Field label="Modèle d'URL BureauxLocaux"><input type="url" value={s.connector_bureauxlocaux_search_template || ''} disabled={ro} placeholder="https://www.bureauxlocaux.com/…" onChange={(e) => set('connector_bureauxlocaux_search_template', e.target.value)} /></Field>
          <Field label="Modèle d'URL Geolocaux"><input type="url" value={s.connector_geolocaux_search_template || ''} disabled={ro} placeholder="https://www.geolocaux.com/…" onChange={(e) => set('connector_geolocaux_search_template', e.target.value)} /></Field>
          {!ro && <div><button className="btn btn-primary" onClick={() => save({ connector_bureauxlocaux_search_template: s.connector_bureauxlocaux_search_template, connector_geolocaux_search_template: s.connector_geolocaux_search_template })}>Enregistrer</button></div>}
        </section>
      )
      return (
        <section className="card card-body stack" style={{ maxWidth: 820 }}>
          <div className="alert info small">
            Intégration facultative pour <b>Outlook classique sous Windows</b> : un petit agent local (dossier <code>outlook-agent</code>) crée des brouillons via Outlook (pywin32), pièces jointes PDF comprises. Il n'écoute que sur 127.0.0.1 et exige un jeton d'appairage. Le <b>nouvel Outlook</b>, macOS, iPhone et Android ne sont pas compatibles avec cette méthode : utilisez « Ouvrir dans la messagerie » ou le fichier <b>.eml</b>.
          </div>
          <label className="check"><input type="checkbox" checked={!!s.outlook_enabled} disabled={ro} onChange={(e) => set('outlook_enabled', e.target.checked)} />Afficher le bouton « Brouillon Outlook »</label>
          <Field label="Adresse de l'agent local"><input type="url" value={s.outlook_agent_url} disabled={ro} onChange={(e) => set('outlook_agent_url', e.target.value)} /></Field>
          {!ro && <div><button className="btn btn-primary" onClick={() => save({ outlook_enabled: !!s.outlook_enabled, outlook_agent_url: s.outlook_agent_url })}>Enregistrer</button></div>}
          <hr style={{ border: 0, borderTop: '1px solid var(--line)', width: '100%' }} />
          <Field label="Jeton d'appairage de CE poste" hint="Affiché par l'agent au démarrage. Conservé uniquement dans ce navigateur."><input type="password" value={token} onChange={(e) => setToken(e.target.value)} /></Field>
          <div className="row">
            <button className="btn" onClick={() => { try { localStorage.setItem('immopro_outlook_token', token) } catch { /* ignoré */ } toast('Jeton enregistré sur ce poste') }}>Enregistrer le jeton</button>
            <button className="btn" onClick={() => testAgent(s.outlook_agent_url)}>Tester la connexion</button>
          </div>
          {agent && <div className={`alert ${agent.ok ? 'ok' : 'danger'} small`}>{agent.ok ? `Agent connecté — Outlook : ${agent.outlook}` : agent.error}</div>}
        </section>
      )
    }}</Loader>
  )
}

function Exports() {
  const toast = useToast()
  const items = [['offres', 'Offres'], ['demandes', 'Demandes'], ['contacts', 'Contacts'], ['entreprises', 'Entreprises'], ['correspondances', 'Correspondances']]
  return (
    <section className="card card-body" style={{ maxWidth: 720 }}>
      <h2 className="mb">Exports</h2>
      {items.map(([k, l]) => (
        <div key={k} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
          <span style={{ flex: 1 }}>{l}</span>
          <button className="btn btn-sm" onClick={() => download(`/api/exports/${k}.xlsx`).catch((e) => toast(e.message, 'error'))}>Excel</button>
          <button className="btn btn-sm" onClick={() => download(`/api/exports/${k}.csv`).catch((e) => toast(e.message, 'error'))}>CSV</button>
        </div>
      ))}
      <p className="small muted">Les exports sont journalisés. Les fichiers contenant des données personnelles doivent être stockés de façon sécurisée et supprimés après usage.</p>
    </section>
  )
}

function Users() {
  const toast = useToast()
  const st = useApi(() => api('/api/users'), [])
  const [form, setForm] = useState(null)
  const [secret, setSecret] = useState(null)
  const create = async () => {
    try { const r = await api('/api/users', { method: 'POST', body: { ...form, email: form.email || null } }); setForm(null); setSecret({ title: 'Mot de passe temporaire', text: r.temporary_password, note: `À transmettre à ${r.user.username} par un canal sûr. Il devra être changé à la première connexion.` }); st.reload() } catch (e) { toast(e.message, 'error') }
  }
  const upd = async (u, body) => { try { await api(`/api/users/${u.id}`, { method: 'PUT', body }); st.reload() } catch (e) { toast(e.message, 'error') } }
  const reset = async (u) => { try { const r = await api(`/api/users/${u.id}/reset-link`, { method: 'POST' }); setSecret({ title: 'Lien de réinitialisation', text: r.url, note: `Lien à usage unique, valable ${r.expires_minutes} minutes.` }) } catch (e) { toast(e.message, 'error') } }
  return (
    <section className="card">
      <div className="card-head"><h2>Utilisateurs</h2><button className="btn btn-accent btn-sm" onClick={() => setForm({ username: '', full_name: '', email: '', role: 'collaborateur' })}>Nouvel utilisateur</button></div>
      <Loader state={st}>{(list) => (
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Identifiant</th><th>Nom</th><th>Rôle</th><th>Actif</th><th className="hide-sm">Dernière connexion</th><th></th></tr></thead>
          <tbody>{list.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td><td>{u.full_name}</td>
              <td><select value={u.role} onChange={(e) => upd(u, { role: e.target.value })} aria-label="Rôle"><option value="admin">Administrateur</option><option value="collaborateur">Collaborateur</option><option value="lecteur">Lecture seule</option></select></td>
              <td><input type="checkbox" checked={u.is_active} onChange={(e) => upd(u, { is_active: e.target.checked })} aria-label="Actif" /></td>
              <td className="hide-sm">{dateTime(u.last_login_at)}</td>
              <td className="nowrap"><button className="btn btn-sm" onClick={() => reset(u)}>Lien de réinitialisation</button> <button className="btn btn-sm" onClick={() => api(`/api/users/${u.id}/revoke-sessions`, { method: 'POST' }).then(() => toast('Sessions fermées'))}>Déconnecter</button></td>
            </tr>))}
          </tbody>
        </table></div>
      )}</Loader>
      {form && (
        <Modal title="Nouvel utilisateur" onClose={() => setForm(null)} footer={<><button className="btn" onClick={() => setForm(null)}>Annuler</button><button className="btn btn-primary" onClick={create}>Créer</button></>}>
          <div className="form-grid">
            <Field label="Identifiant"><input type="text" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} autoCapitalize="none" /></Field>
            <Field label="Nom complet"><input type="text" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Email"><input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Rôle"><select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><option value="collaborateur">Collaborateur (lecture + écriture)</option><option value="lecteur">Lecture seule</option><option value="admin">Administrateur</option></select></Field>
          </div>
          <p className="small muted">Un mot de passe temporaire aléatoire sera généré et affiché une seule fois.</p>
        </Modal>
      )}
      {secret && (
        <Modal title={secret.title} onClose={() => setSecret(null)}>
          <input type="text" readOnly value={secret.text} onFocus={(e) => e.target.select()} />
          <p className="small muted">{secret.note} Il ne sera plus affiché ensuite.</p>
        </Modal>
      )}
    </section>
  )
}

function Backups() {
  const toast = useToast()
  const st = useApi(() => api('/api/backups'), [])
  const make = async () => { try { await api('/api/backups', { method: 'POST' }); toast('Sauvegarde créée'); st.reload() } catch (e) { toast(e.message, 'error') } }
  return (
    <section className="card">
      <div className="card-head"><h2>Sauvegardes</h2><button className="btn btn-primary btn-sm" onClick={make}>Sauvegarder maintenant</button></div>
      <Loader state={st}>{(d) => (
        <div className="card-body">
          <p className="small muted">Sauvegarde automatique {d.interval_hours > 0 ? `toutes les ${d.interval_hours} h` : 'désactivée'} · conservation des {d.keep} dernières. La restauration se fait en ligne de commande, application arrêtée (voir documentation).</p>
          {!d.backups.length ? <div className="muted small">Aucune sauvegarde.</div> : d.backups.map((b) => (
            <div key={b.name} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ flex: 1 }}>{b.name}</span><span className="small muted">{Math.round(b.size / 1024)} Ko · {dateTime(b.created_at)}</span>
              <button className="btn btn-sm" onClick={() => download(`/api/backups/${b.name}`)}>Télécharger</button>
            </div>
          ))}
        </div>
      )}</Loader>
    </section>
  )
}

function Audit() {
  const st = useApi(() => api('/api/audit', { params: { limit: 300 } }), [])
  return (
    <section className="card">
      <div className="card-head"><h2>Journal des opérations</h2></div>
      <Loader state={st}>{(list) => (
        <div className="table-wrap"><table className="table">
          <thead><tr><th>Date</th><th>Utilisateur</th><th>Action</th><th className="hide-sm">Élément</th><th className="hide-sm">IP</th></tr></thead>
          <tbody>{list.map((a) => (
            <tr key={a.id}><td className="nowrap">{dateTime(a.at)}</td><td>{a.username || '—'}</td><td>{a.action}</td><td className="hide-sm small">{a.entity}{a.entity_id ? ` #${a.entity_id}` : ''} {a.details ? JSON.stringify(a.details).slice(0, 80) : ''}</td><td className="hide-sm small">{a.ip}</td></tr>
          ))}</tbody>
        </table></div>
      )}</Loader>
    </section>
  )
}
