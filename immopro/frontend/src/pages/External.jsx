import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import ContactCard from '../components/ContactCard.jsx'
import Icon from '../components/Icon.jsx'
import { Empty, Field, Loader, Modal, Score, useApi, useToast } from '../components/ui.jsx'
import { TRANSACTION_LABELS, TYPE_LABELS, dateTime, eur, num } from '../format.js'
import PropertyForm from './PropertyForm.jsx'
import { MatchList } from './RequestDetail.jsx'

const SOURCE_NAMES = { bureauxlocaux: 'BureauxLocaux', geolocaux: 'Geolocaux', autre: 'Autre source' }
const PRICE_KIND = { vente: 'Prix de vente', loyer_annuel: 'Loyer annuel', loyer_m2_an: 'Loyer €/m²/an' }

// Bouton « Rechercher des biens » d'une demande : base interne + BureauxLocaux + Geolocaux.
export function ExternalSearchPanel({ request, setModal }) {
  const toast = useToast()
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [adding, setAdding] = useState(null)
  const [saving, setSaving] = useState(null)
  const run = async () => {
    setBusy(true)
    try { setRes(await api(`/api/external/search/${request.id}`, { method: 'POST' })) } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  const copyCriteria = async (s) => {
    try { await navigator.clipboard.writeText(s.criteria.map((c) => `${c.label} : ${c.value}`).join('\n')); toast('Critères copiés') } catch { toast('Copie impossible', 'error') }
  }
  return (
    <div className="stack">
      <div className="card card-body row">
        <div style={{ flex: 1, minWidth: 240 }}>
          <b>Recherche multisource</b>
          <div className="small muted">Applique les critères enregistrés de la demande à la base interne, et prépare les recherches sur BureauxLocaux et Geolocaux.</div>
        </div>
        <button className="btn btn-accent" onClick={run} disabled={busy}><Icon name="search" />{busy ? 'Recherche…' : res ? 'Relancer la recherche' : 'Rechercher des biens'}</button>
      </div>
      {res && (
        <>
          <div className="small muted">Recherche effectuée le {dateTime(res.searched_at)} (enregistrée dans l'historique).</div>
          <h2>Base interne <span className="badge teal">{res.internal.length}</span></h2>
          <MatchList list={res.internal} request={request} setModal={setModal} />
          <h2 className="mt">Plateformes externes</h2>
          <div className="grid g2">
            {res.sources.map((s) => (
              <section key={s.key} className="card card-body stack" style={{ gap: 10 }}>
                <div className="row"><h3>{s.name}</h3><span className="badge warn">Recherche automatique indisponible</span></div>
                <div className="small muted">{s.message}</div>
                <div className="small">{s.link.note}</div>
                {s.criteria.length > 0 && (
                  <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>{s.criteria.map((c) => <li key={c.label}><b>{c.label} :</b> {c.value}</li>)}</ul>
                )}
                <div className="row">
                  <a className="btn btn-primary btn-sm" href={s.link.url} target="_blank" rel="noopener noreferrer"><Icon name="external" />Ouvrir {s.name}</a>
                  <button className="btn btn-sm" onClick={() => copyCriteria(s)}><Icon name="copy" />Copier les critères</button>
                  <button className="btn btn-sm" onClick={() => setAdding({ source: s.key, search_id: res.search_id })}><Icon name="plus" />Importer une annonce</button>
                </div>
              </section>
            ))}
          </div>
          <h2 className="mt">Annonces externes enregistrées <span className="badge">{res.external_listings.length}</span></h2>
          {!res.external_listings.length ? <div className="muted small">Aucune annonce externe compatible enregistrée. Importez les annonces repérées sur les plateformes.</div> : res.external_listings.map((l) => (
            <ListingCard key={l.id} l={l} onSave={() => setSaving(l)} onReload={run} />
          ))}
        </>
      )}
      {adding && <ListingForm initial={adding} onClose={() => setAdding(null)} onSaved={() => { setAdding(null); run() }} />}
      {saving && <SaveListing listing={saving} onClose={() => setSaving(null)} onSaved={() => { setSaving(null); run() }} />}
    </div>
  )
}

function ListingCard({ l, onSave, onReload }) {
  const toast = useToast()
  const { can } = useAuth()
  const check = async (still) => { try { await api(`/api/external/listings/${l.id}/check`, { method: 'POST', body: { still_online: still } }); toast('Vérification enregistrée'); onReload && onReload() } catch (e) { toast(e.message, 'error') } }
  const contact = l.advertiser_name || l.advertiser_phone || l.advertiser_email ? { display_name: l.advertiser_name, phone: l.advertiser_phone, email: l.advertiser_email, is_public_listing_contact: true } : null
  return (
    <article className="card card-body">
      <div className="row" style={{ alignItems: 'flex-start' }}>
        {l.match && <Score value={l.match.score} />}
        <div style={{ flex: 1, minWidth: 220 }}>
          <div className="row">
            <span className="badge navy">Externe · {SOURCE_NAMES[l.source]}</span>
            {l.fresh ? <span className="badge ok">Vérifiée &lt; {l.freshness_days} j</span> : <span className="badge warn">À revérifier</span>}
            {l.still_online === false && <span className="badge danger">Retirée</span>}
            {l.imported_property_id && <Link className="badge teal" to={`/offres/${l.imported_property_id}`}>Enregistrée en base</Link>}
          </div>
          <h3 style={{ marginTop: 4 }}>{l.title || 'Annonce sans titre'}</h3>
          <div className="small muted">{[TYPE_LABELS[l.property_type], TRANSACTION_LABELS[l.transaction], [l.postal_code, l.city].filter(Boolean).join(' '), l.surface && num(l.surface, 'm²'), l.price && `${PRICE_KIND[l.price_kind] || 'Prix'} : ${l.price_kind === 'loyer_m2_an' ? num(l.price) + ' €' : eur(l.price)}`].filter(Boolean).join(' · ')}</div>
          {l.features && <div className="small">{l.features}</div>}
          <div className="small muted">Consultée le {dateTime(l.consulted_at)}{l.last_checked_at ? ` · vérifiée le ${dateTime(l.last_checked_at)}` : ''}</div>
          <a className="small" href={l.url} target="_blank" rel="noopener noreferrer">{l.url} <Icon name="external" size={12} /></a>
          {l.duplicates?.length > 0 && <div className="small" style={{ color: 'var(--warn)' }}>Doublon probable avec : {l.duplicates.map((d) => <Link key={d.id} to={`/offres/${d.id}`}> {d.title || d.reference || '#' + d.id}</Link>)}</div>}
          {l.match?.missing?.length > 0 && <div className="small muted">À vérifier : {l.match.missing.slice(0, 3).join(' · ')}</div>}
        </div>
        {can('write') && (
          <div className="row">
            <button className="btn btn-sm" onClick={() => check(true)}>Toujours en ligne</button>
            <button className="btn btn-sm" onClick={() => check(false)}>Retirée</button>
            {!l.imported_property_id && <button className="btn btn-sm btn-primary" onClick={onSave}>Enregistrer dans la base</button>}
          </div>
        )}
      </div>
      {contact && <div className="mt"><ContactCard title="Annonceur (coordonnées publiques)" contact={contact} /></div>}
    </article>
  )
}

function ListingForm({ initial, onClose, onSaved }) {
  const toast = useToast()
  const [f, setF] = useState({ url: '', title: '', property_type: '', transaction: '', city: '', postal_code: '', surface: '', price: '', price_kind: '', features: '', advertiser_name: '', advertiser_phone: '', advertiser_email: '', search_id: initial?.search_id })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const save = async () => {
    const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v === '' ? null : v]))
    body.surface = body.surface ? Number(String(body.surface).replace(',', '.')) : null
    body.price = body.price ? Number(String(body.price).replace(/\s/g, '').replace(',', '.')) : null
    try { await api('/api/external/listings', { method: 'POST', body }); toast('Annonce enregistrée'); onSaved() } catch (e) { toast(e.message, 'error') }
  }
  return (
    <Modal title="Importer une annonce externe" onClose={onClose} footer={<><button className="btn" onClick={onClose}>Annuler</button><button className="btn btn-primary" onClick={save}>Enregistrer l'annonce</button></>}>
      <div className="alert info small mb">Copiez l'URL de l'annonce consultée et reportez uniquement les informations qui y figurent. Les coordonnées de l'annonceur ne doivent être saisies que si elles sont publiques et que leur usage est autorisé.</div>
      <div className="form-grid">
        <Field label="URL de l'annonce *" wide><input type="url" value={f.url} onChange={set('url')} placeholder="https://www.geolocaux.com/…" required /></Field>
        <Field label="Titre" wide><input type="text" value={f.title} onChange={set('title')} /></Field>
        <Field label="Type"><select value={f.property_type} onChange={set('property_type')}><option value="">—</option>{Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        <Field label="Transaction"><select value={f.transaction} onChange={set('transaction')}><option value="">—</option><option value="vente">Vente</option><option value="location">Location</option></select></Field>
        <Field label="Code postal"><input type="text" value={f.postal_code} onChange={set('postal_code')} /></Field>
        <Field label="Ville"><input type="text" value={f.city} onChange={set('city')} /></Field>
        <Field label="Surface (m²)"><input type="text" inputMode="decimal" value={f.surface} onChange={set('surface')} /></Field>
        <Field label="Prix / loyer"><input type="text" inputMode="decimal" value={f.price} onChange={set('price')} /></Field>
        <Field label="Nature du prix"><select value={f.price_kind} onChange={set('price_kind')}><option value="">—</option>{Object.entries(PRICE_KIND).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        <Field label="Caractéristiques" wide><textarea value={f.features} onChange={set('features')} /></Field>
        <Field label="Annonceur"><input type="text" value={f.advertiser_name} onChange={set('advertiser_name')} /></Field>
        <Field label="Téléphone annonceur"><input type="tel" value={f.advertiser_phone} onChange={set('advertiser_phone')} /></Field>
        <Field label="Email annonceur"><input type="email" value={f.advertiser_email} onChange={set('advertiser_email')} /></Field>
      </div>
    </Modal>
  )
}

function SaveListing({ listing: l, onClose, onSaved }) {
  const initial = {
    title: l.title, property_type: l.property_type, transaction: l.transaction, city: l.city, postal_code: l.postal_code, surface_total: l.surface,
    sale_price: l.price_kind === 'vente' ? l.price : null, annual_rent: l.price_kind === 'loyer_annuel' ? l.price : null, rent_per_sqm: l.price_kind === 'loyer_m2_an' ? l.price : null,
    description: l.features, status: 'active',
  }
  return (
    <Modal title="Valider et enregistrer dans la base" onClose={onClose} wide>
      <div className="alert info small mb">Vérifiez chaque champ avant l'enregistrement. L'URL et la date de consultation de l'annonce sont conservées comme source.</div>
      <PropertyForm embedded initial={initial} submitUrl={`/api/external/listings/${l.id}/to-property`} onSaved={onSaved} />
    </Modal>
  )
}

export default function External() {
  const [q, setQ] = useState('')
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(null)
  const { can } = useAuth()
  const st = useApi(() => api('/api/external/listings', { params: { q } }), [q])
  const hist = useApi(() => api('/api/external/searches'), [])
  const conn = useApi(() => api('/api/external/connectors'), [])
  return (
    <>
      <div className="page-head">
        <div><h1>Annonces externes</h1><p>Annonces repérées sur BureauxLocaux, Geolocaux ou ailleurs, importées manuellement.</p></div>
        {can('write') && <button className="btn btn-accent" onClick={() => setAdding(true)}><Icon name="plus" />Importer une annonce</button>}
      </div>
      <Loader state={conn}>{(cs) => (
        <div className="grid g2 mb">{cs.map((c) => (
          <div key={c.key} className="card card-body small">
            <div className="row"><b>{c.name}</b><span className="badge warn">{c.mode === 'lien_parametre' ? 'Lien paramétré (modèle utilisateur)' : 'Lien simple'}</span><div className="spacer" /><a href={c.base_url} target="_blank" rel="noopener noreferrer">Ouvrir <Icon name="external" size={12} /></a></div>
            <div className="muted">{c.status}</div>
          </div>))}
        </div>
      )}</Loader>
      <div className="split">
        <div className="stack">
          <input type="search" placeholder="Filtrer (titre, ville)" value={q} onChange={(e) => setQ(e.target.value)} />
          <Loader state={st}>{(list) => !list.length ? <Empty icon="globe">Aucune annonce externe enregistrée.</Empty> : list.map((l) => <ListingCard key={l.id} l={l} onSave={() => setSaving(l)} onReload={st.reload} />)}</Loader>
        </div>
        <section className="card">
          <div className="card-head"><h2>Historique des recherches</h2></div>
          <div className="card-body">
            <Loader state={hist}>{(h) => !h.length ? <div className="muted small">Aucune recherche.</div> : h.map((s) => (
              <div key={s.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                <Link to={`/demandes/${s.request_id}`}><b>{s.request_label || `Demande #${s.request_id}`}</b></Link>
                <div className="small muted">{dateTime(s.created_at)} · {s.results_summary?.internes ?? 0} interne(s), {s.results_summary?.externes_enregistrees ?? 0} externe(s)</div>
              </div>))}
            </Loader>
          </div>
        </section>
      </div>
      {adding && <ListingForm onClose={() => setAdding(false)} onSaved={() => { setAdding(false); st.reload() }} />}
      {saving && <SaveListing listing={saving} onClose={() => setSaving(null)} onSaved={() => { setSaving(null); st.reload() }} />}
    </>
  )
}
