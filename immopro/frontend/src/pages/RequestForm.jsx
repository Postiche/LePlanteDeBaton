import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import ContactSelect from '../components/ContactSelect.jsx'
import { Chips, Field, Modal, useApi, useToast } from '../components/ui.jsx'
import { IMPERATIVES, PRIORITIES, REGIONS, REQUEST_STATUS, TYPE_LABELS } from '../format.js'
import { cleanPayload } from './PropertyForm.jsx'

const NUM = ['center_latitude', 'center_longitude', 'radius_km', 'surface_min', 'surface_max', 'budget_max', 'budget_per_sqm_max', 'min_clear_height', 'min_docks', 'min_floor_load', 'min_power_kva', 'min_parking']
const LISTS = ['cities', 'postal_codes', 'departments']

export default function RequestForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const companies = useApi(() => api('/api/companies'), [])
  const [f, setF] = useState({ status: 'active', priority: 'normale', property_types: [], regions: [], imperatives: [] })
  const [dups, setDups] = useState(null)
  useEffect(() => {
    if (id) api(`/api/requests/${id}`).then((r) => setF({ ...r, ...Object.fromEntries(LISTS.map((k) => [k, (r[k] || []).join(', ')])) })).catch((e) => toast(e.message, 'error'))
  }, [id]) // eslint-disable-line
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const val = (k) => f[k] ?? ''
  const save = async (force) => {
    const body = cleanPayload(f, NUM)
    LISTS.forEach((k) => { body[k] = String(f[k] || '').split(/[,;]+/).map((x) => x.trim()).filter(Boolean) })
    if (body.min_docks != null) body.min_docks = Math.round(body.min_docks)
    if (body.min_parking != null) body.min_parking = Math.round(body.min_parking)
    try {
      const r = id ? await api(`/api/requests/${id}`, { method: 'PUT', body }) : await api('/api/requests', { method: 'POST', body, params: force ? { force: true } : undefined })
      toast('Demande enregistrée — correspondances recalculées')
      nav(`/demandes/${r.id}`)
    } catch (e) {
      if (e.status === 409) setDups(e.detail.duplicates)
      else toast(e.message, 'error')
    }
  }
  const N = (k, label, hint) => <Field label={label} hint={hint}><input type="text" inputMode="decimal" value={val(k)} onChange={set(k)} /></Field>
  return (
    <form onSubmit={(e) => { e.preventDefault(); save() }}>
      <div className="page-head"><div><h1>{id ? 'Modifier la demande' : 'Nouvelle demande client'}</h1><p>Les critères non renseignés ne sont pas pris en compte. Marquez comme impératifs uniquement les critères explicitement non négociables.</p></div></div>
      <fieldset><legend>Client</legend>
        <div className="form-grid">
          <ContactSelect label="Contact (CRM)" kind="client" value={f.contact_id} onChange={(v) => setF({ ...f, contact_id: v })} />
          <Field label="Entreprise (CRM)"><select value={val('company_id')} onChange={(e) => setF({ ...f, company_id: e.target.value ? +e.target.value : null })}><option value="">—</option>{(companies.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Client / société (texte libre)"><input type="text" value={val('client_name')} onChange={set('client_name')} /></Field>
          <Field label="Interlocuteur"><input type="text" value={val('contact_name')} onChange={set('contact_name')} /></Field>
          <Field label="Email"><input type="email" value={val('email')} onChange={set('email')} /></Field>
          <Field label="Téléphone"><input type="tel" value={val('phone')} onChange={set('phone')} /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Recherche</legend>
        <div className="form-grid">
          <Field label="Intitulé" wide><input type="text" value={val('title')} onChange={set('title')} placeholder="ex. Entrepôt 8 000 m² Est lyonnais" /></Field>
          <Field label="Référence"><input type="text" value={val('reference')} onChange={set('reference')} /></Field>
          <Field label="Transaction"><select value={val('transaction')} onChange={set('transaction')}><option value="">Vente ou location</option><option value="vente">Achat</option><option value="location">Location</option></select></Field>
          <Field label="Date de la demande"><input type="date" value={val('request_date')} onChange={set('request_date')} /></Field>
          <Field label="Priorité"><select value={val('priority')} onChange={set('priority')}>{Object.entries(PRIORITIES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Statut"><select value={val('status')} onChange={set('status')}>{Object.entries(REQUEST_STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <div className="field wide"><span>Types de bien recherchés</span><Chips options={TYPE_LABELS} value={f.property_types || []} onChange={(v) => setF({ ...f, property_types: v })} /></div>
        </div>
      </fieldset>
      <fieldset><legend>Localisation</legend>
        <div className="form-grid">
          <Field label="Communes" hint="Séparées par des virgules"><input type="text" value={val('cities')} onChange={set('cities')} /></Field>
          <Field label="Codes postaux"><input type="text" value={val('postal_codes')} onChange={set('postal_codes')} /></Field>
          <Field label="Départements" hint="ex. 69, 38, 01"><input type="text" value={val('departments')} onChange={set('departments')} /></Field>
          <Field label="Centre du rayon"><input type="text" value={val('center_label')} onChange={set('center_label')} placeholder="ex. Lyon" /></Field>
          {N('center_latitude', 'Latitude du centre')}
          {N('center_longitude', 'Longitude du centre')}
          {N('radius_km', 'Rayon (km)', 'Nécessite des coordonnées de centre')}
          <div className="field wide"><span>Régions</span><Chips options={Object.fromEntries(REGIONS.map((r) => [r, r]))} value={f.regions || []} onChange={(v) => setF({ ...f, regions: v })} /></div>
        </div>
      </fieldset>
      <fieldset><legend>Surface, budget et disponibilité</legend>
        <div className="form-grid">
          {N('surface_min', 'Surface minimale (m²)')}
          {N('surface_max', 'Surface maximale (m²)')}
          {N('budget_max', 'Budget maximum (€)', 'Prix total (achat) ou loyer annuel HT HC (location)')}
          {N('budget_per_sqm_max', 'Budget max au m² (€)')}
          <Field label="Disponibilité souhaitée"><input type="date" value={val('desired_date')} onChange={set('desired_date')} /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Contraintes techniques</legend>
        <div className="form-grid">
          {N('min_clear_height', 'Hauteur libre min (m)')}
          {N('min_docks', 'Quais min')}
          {N('min_floor_load', 'Résistance au sol min (t/m²)')}
          {N('min_power_kva', 'Puissance min (kVA)')}
          {N('min_parking', 'Places de parking min')}
          <Field label="Accès poids lourds"><select value={f.requires_hgv_access ? 'true' : ''} onChange={(e) => setF({ ...f, requires_hgv_access: e.target.value === 'true' ? true : null })}><option value="">Non exigé</option><option value="true">Exigé</option></select></Field>
          <Field label="Autres contraintes" wide><textarea value={val('other_constraints')} onChange={set('other_constraints')} /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Critères impératifs (éliminatoires)</legend>
        <p className="small muted" style={{ marginTop: 0 }}>Un bien qui ne satisfait pas un critère impératif est écarté. Un bien dont l'information est manquante n'est jamais écarté : il est signalé « à vérifier ». Les autres critères sont souhaitables et pondèrent le score.</p>
        <Chips imperative options={IMPERATIVES} value={f.imperatives || []} onChange={(v) => setF({ ...f, imperatives: v })} />
      </fieldset>
      <fieldset><legend>Commentaires</legend><textarea value={val('comments')} onChange={set('comments')} /></fieldset>
      <div className="row"><button className="btn btn-primary">Enregistrer</button><button type="button" className="btn" onClick={() => nav(-1)}>Annuler</button></div>
      {dups && (
        <Modal title="Demande similaire existante" onClose={() => setDups(null)} footer={<><button type="button" className="btn" onClick={() => setDups(null)}>Revenir</button><button type="button" className="btn btn-primary" onClick={() => { setDups(null); save(true) }}>Créer quand même</button></>}>
          <ul>{dups.map((d) => <li key={d.id}><a href={`/demandes/${d.id}`} target="_blank" rel="noreferrer">{d.title || d.reference || d.client_name}</a></li>)}</ul>
        </Modal>
      )}
    </form>
  )
}
