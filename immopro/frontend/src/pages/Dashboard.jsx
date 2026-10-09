import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { Columns, HBars } from '../components/Charts.jsx'
import { Loader, Score, useApi } from '../components/ui.jsx'
import { INTERACTION_KINDS, dateTime } from '../format.js'

export default function Dashboard() {
  const [days, setDays] = useState(30)
  const [demo, setDemo] = useState('all')
  const nav = useNavigate()
  const st = useApi(() => api('/api/dashboard', { params: { days, demo } }), [days, demo])
  return (
    <>
      <div className="page-head">
        <div><h1>Tableau de bord</h1><p>Activité commerciale et portefeuille</p></div>
        <div className="row">
          <select value={days} onChange={(e) => setDays(+e.target.value)} aria-label="Période" style={{ width: 'auto' }}>
            {[7, 30, 90, 365].map((d) => <option key={d} value={d}>{d === 365 ? '12 mois' : `${d} jours`}</option>)}
          </select>
          <select value={demo} onChange={(e) => setDemo(e.target.value)} aria-label="Données" style={{ width: 'auto' }}>
            <option value="all">Toutes les données</option><option value="real">Données réelles</option><option value="demo">Démonstration</option>
          </select>
        </div>
      </div>
      <Loader state={st}>{(d) => (
        <div className="stack">
          <div className="grid g4">
            <Kpi accent label="Offres actives" value={d.kpis.offres} to="/offres" />
            <Kpi label="Demandes clients" value={d.kpis.demandes} sub={`${d.kpis.demandes_actives} actives`} to="/demandes" />
            <Kpi label="Nouveaux biens" value={d.kpis.nouveaux_biens} sub={`sur ${days} jours`} to="/offres?sort=-created_at" />
            <Kpi label="Correspondances" value={d.kpis.correspondances} sub="au-dessus du seuil" to="/correspondances" />
            <Kpi label="Demandes actives" value={d.kpis.demandes_actives} to="/demandes" />
            <Kpi label="Visites proposées" value={d.kpis.visites_proposees} to="/visites" />
            <Kpi label="Visites confirmées" value={d.kpis.visites_confirmees} to="/visites" />
            <Kpi label="Contacts à relancer" value={d.kpis.relances} sub="échéance ≤ 24 h" to="/relances" />
          </div>
          <div className="grid g2">
            <section className="card"><div className="card-head"><h2>Pipeline des correspondances</h2></div><div className="card-body"><HBars data={d.matches_by_status} onClick={(x) => nav(`/correspondances?status=${x.key}`)} /></div></section>
            <section className="card"><div className="card-head"><h2>Offres actives par type</h2></div><div className="card-body"><HBars data={d.properties_by_type} onClick={(x) => nav(`/offres?property_type=${x.key}`)} /></div></section>
          </div>
          <div className="grid g2">
            <section className="card"><div className="card-head"><h2>Nouveaux biens par semaine</h2></div><div className="card-body"><Columns data={d.new_properties_by_week} label="Nouveaux biens par semaine" /></div></section>
            <section className="card"><div className="card-head"><h2>Meilleures correspondances à traiter</h2><Link to="/correspondances" className="small">Tout voir</Link></div>
              <div className="card-body">
                {!d.top_matches.length ? <div className="muted small">Aucune correspondance à contacter.</div> : d.top_matches.map((m) => (
                  <div key={m.id} className="row" style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                    <Score value={m.score} small />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Link to={`/offres/${m.property.id}`}><b>{m.property.title || m.property.reference}</b></Link>
                      <div className="small muted">pour <Link to={`/demandes/${m.request.id}`}>{m.request.client_name || m.request.title}</Link></div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
          <div className="grid g2">
            <section className="card"><div className="card-head"><h2>Contacts à relancer</h2><Link to="/relances" className="small">Tout voir</Link></div>
              <div className="card-body">{!d.reminders.length ? <div className="muted small">Aucune relance en attente.</div> : d.reminders.map((r) => (
                <div key={r.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <b>{r.subject}</b><div className="small muted">{dateTime(r.remind_at)} · {r.contact_name || r.request_label || r.property_label || ''}</div>
                </div>))}
              </div>
            </section>
            <section className="card"><div className="card-head"><h2>Activité commerciale récente</h2></div>
              <div className="card-body">{!d.recent_activity.length ? <div className="muted small">Aucune activité.</div> : d.recent_activity.map((r) => (
                <div key={r.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                  <span className="badge">{INTERACTION_KINDS[r.kind] || r.kind}</span> <b>{r.subject}</b>
                  <div className="small muted">{dateTime(r.at)} {r.contact_name ? `· ${r.contact_name}` : ''} {r.property_label ? `· ${r.property_label}` : ''}</div>
                </div>))}
              </div>
            </section>
          </div>
        </div>
      )}</Loader>
    </>
  )
}

function Kpi({ label, value, sub, to, accent }) {
  return (
    <Link to={to} className={`card kpi ${accent ? 'accent' : ''}`} style={{ color: 'inherit' }}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </Link>
  )
}
