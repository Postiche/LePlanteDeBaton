import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api.js'
import ContactSelect from '../components/ContactSelect.jsx'
import { Field, Modal, useToast } from '../components/ui.jsx'
import { PROPERTY_STATUS, TYPE_LABELS } from '../format.js'

const NUM = ['latitude', 'longitude', 'surface_total', 'surface_divisible_min', 'surface_offices', 'surface_storage', 'land_area', 'clear_height', 'dock_count', 'sectional_doors', 'floor_load', 'power_kva', 'parking_spaces', 'sale_price', 'annual_rent', 'rent_per_sqm', 'charges', 'property_tax']

export function cleanPayload(f, numeric) {
  const out = {}
  for (const [k, v] of Object.entries(f)) {
    if (['id', 'created_at', 'updated_at', 'documents', 'duplicates', 'owner_contact', 'agency_contact', 'sales_contact', 'cover_photo_id', 'is_demo', 'created_by', 'match_count', 'company_name', 'display_client', 'contact', 'source_consulted_at', 'geocode_status'].includes(k)) continue
    if (numeric.includes(k)) out[k] = v === '' || v === null || v === undefined ? null : Number(String(v).replace(',', '.').replace(/\s/g, ''))
    else if (v === '') out[k] = null
    else out[k] = v
  }
  return out
}

export default function PropertyForm({ initial, onSaved, embedded, submitUrl }) {
  const params = useParams()
  const id = embedded ? null : params.id
  const nav = useNavigate()
  const toast = useToast()
  const [f, setF] = useState(initial || { status: 'active' })
  const [dups, setDups] = useState(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { if (id && !initial) api(`/api/properties/${id}`).then(setF).catch((e) => toast(e.message, 'error')) }, [id]) // eslint-disable-line
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const val = (k) => f[k] ?? ''
  const save = async (force = false) => {
    setBusy(true)
    try {
      const body = cleanPayload(f, NUM)
      if (body.hgv_access === '') body.hgv_access = null
      const res = id
        ? await api(`/api/properties/${id}`, { method: 'PUT', body })
        : await api(submitUrl || '/api/properties', { method: 'POST', body, params: force ? { force: true } : undefined })
      toast('Offre enregistrée — correspondances recalculées')
      if (onSaved) onSaved(res)
      else nav(`/offres/${res.id}`)
    } catch (e) {
      if (e.status === 409) setDups(e.detail.duplicates)
      else toast(e.message, 'error')
    } finally { setBusy(false) }
  }
  const N = (k, label, hint) => <Field label={label} hint={hint}><input type="text" inputMode="decimal" value={val(k)} onChange={set(k)} /></Field>
  return (
    <form onSubmit={(e) => { e.preventDefault(); save() }}>
      {!embedded && <div className="page-head"><div><h1>{id ? 'Modifier l\'offre' : 'Nouvelle offre'}</h1><p>Seules les informations connues doivent être saisies : un champ vide reste « non renseigné ».</p></div></div>}
      <fieldset><legend>Identification</legend>
        <div className="form-grid">
          <Field label="Référence"><input type="text" value={val('reference')} onChange={set('reference')} /></Field>
          <Field label="Titre" wide><input type="text" value={val('title')} onChange={set('title')} /></Field>
          <Field label="Type de bien"><select value={val('property_type')} onChange={set('property_type')}><option value="">Non renseigné</option>{Object.entries(TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Transaction"><select value={val('transaction')} onChange={set('transaction')}><option value="">Non renseignée</option><option value="vente">Vente</option><option value="location">Location</option><option value="vente_ou_location">Vente ou location</option></select></Field>
          <Field label="Statut"><select value={val('status')} onChange={set('status')}>{Object.entries(PROPERTY_STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="État du bien"><input type="text" value={val('condition')} onChange={set('condition')} placeholder="Neuf, rénové, à rafraîchir…" /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Localisation</legend>
        <div className="form-grid">
          <Field label="Adresse" wide><input type="text" value={val('address')} onChange={set('address')} /></Field>
          <Field label="Code postal"><input type="text" inputMode="numeric" maxLength={5} value={val('postal_code')} onChange={set('postal_code')} /></Field>
          <Field label="Ville"><input type="text" value={val('city')} onChange={set('city')} /></Field>
          {N('latitude', 'Latitude', 'Facultatif : géocodage automatique sinon')}
          {N('longitude', 'Longitude')}
        </div>
      </fieldset>
      <fieldset><legend>Surfaces et caractéristiques techniques</legend>
        <div className="form-grid">
          {N('surface_total', 'Surface totale (m²)')}
          {N('surface_divisible_min', 'Divisible à partir de (m²)')}
          {N('surface_storage', 'Stockage / activité (m²)')}
          {N('surface_offices', 'Bureaux (m²)')}
          {N('land_area', 'Terrain (m²)')}
          {N('clear_height', 'Hauteur libre (m)')}
          {N('dock_count', 'Quais')}
          {N('sectional_doors', 'Portes sectionnelles')}
          <Field label="Accès poids lourds"><select value={f.hgv_access === true ? 'true' : f.hgv_access === false ? 'false' : ''} onChange={(e) => setF({ ...f, hgv_access: e.target.value === '' ? null : e.target.value === 'true' })}><option value="">Non renseigné</option><option value="true">Oui</option><option value="false">Non</option></select></Field>
          {N('floor_load', 'Résistance au sol (t/m²)')}
          {N('power_kva', 'Puissance électrique (kVA)')}
          {N('parking_spaces', 'Places de parking')}
          <Field label="Disponible le"><input type="date" value={val('available_from')} onChange={set('available_from')} /></Field>
          <Field label="Disponibilité (texte)"><input type="text" value={val('availability_note')} onChange={set('availability_note')} placeholder="Immédiate, 3 mois après préavis…" /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Conditions financières</legend>
        <div className="form-grid">
          {N('sale_price', 'Prix de vente (€)')}
          {N('annual_rent', 'Loyer annuel HT HC (€)')}
          {N('rent_per_sqm', 'Loyer (€/m²/an)')}
          {N('charges', 'Charges annuelles (€)')}
          {N('property_tax', 'Taxe foncière (€)')}
          <Field label="Honoraires"><input type="text" value={val('fees')} onChange={set('fees')} /></Field>
        </div>
      </fieldset>
      <fieldset><legend>Description</legend><textarea value={val('description')} onChange={set('description')} style={{ minHeight: 140 }} /></fieldset>
      <fieldset><legend>Intervenants</legend>
        <div className="form-grid">
          <ContactSelect label="Propriétaire" value={f.owner_contact_id} onChange={(v) => setF({ ...f, owner_contact_id: v })} />
          <ContactSelect label="Agence / annonceur" value={f.agency_contact_id} onChange={(v) => setF({ ...f, agency_contact_id: v })} />
          <ContactSelect label="Commercial (contact affiché sur les fiches)" value={f.sales_contact_id} onChange={(v) => setF({ ...f, sales_contact_id: v })} />
        </div>
      </fieldset>
      <fieldset><legend>Provenance</legend>
        <div className="form-grid">
          <Field label="Source"><input type="text" value={val('source_name')} onChange={set('source_name')} placeholder="Mandat direct, confrère, annonce…" /></Field>
          <Field label="URL d'origine"><input type="url" value={val('source_url')} onChange={set('source_url')} /></Field>
          <Field label="Référence source"><input type="text" value={val('source_ref')} onChange={set('source_ref')} /></Field>
        </div>
      </fieldset>
      <div className="row"><button className="btn btn-primary" disabled={busy}>{busy ? 'Enregistrement…' : 'Enregistrer'}</button>{!embedded && <button type="button" className="btn" onClick={() => nav(-1)}>Annuler</button>}</div>
      {dups && (
        <Modal title="Doublon probable" onClose={() => setDups(null)} footer={<><button type="button" className="btn" onClick={() => setDups(null)}>Revenir au formulaire</button><button type="button" className="btn btn-primary" onClick={() => { setDups(null); save(true) }}>Enregistrer quand même</button></>}>
          <p>Des offres existantes semblent correspondre :</p>
          <ul>{dups.map((d) => <li key={d.id}><a href={`/offres/${d.id}`} target="_blank" rel="noreferrer">{d.title || d.reference || `Offre #${d.id}`}</a> — {d.city} — {d.reasons.join(', ')}</li>)}</ul>
        </Modal>
      )}
    </form>
  )
}
