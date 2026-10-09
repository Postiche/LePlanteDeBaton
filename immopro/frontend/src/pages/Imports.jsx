import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import Icon from '../components/Icon.jsx'
import { Loader, useApi, useToast } from '../components/ui.jsx'
import { IMPERATIVES, TYPE_LABELS, dateTime } from '../format.js'

const PROPERTY_FIELDS = {
  reference: 'Référence', title: 'Titre', property_type: 'Type de bien', transaction: 'Transaction', address: 'Adresse', postal_code: 'Code postal', city: 'Ville',
  surface_total: 'Surface totale (m²)', surface_divisible_min: 'Divisible dès (m²)', surface_offices: 'Bureaux (m²)', surface_storage: 'Stockage (m²)', land_area: 'Terrain (m²)',
  clear_height: 'Hauteur libre (m)', dock_count: 'Quais', sectional_doors: 'Portes sectionnelles', hgv_access: 'Accès PL', floor_load: 'Résistance sol (t/m²)',
  power_kva: 'Puissance (kVA)', parking_spaces: 'Parking', condition: 'État', available_from: 'Disponible le', availability_note: 'Disponibilité',
  sale_price: 'Prix de vente (€)', annual_rent: 'Loyer annuel (€)', rent_per_sqm: 'Loyer €/m²/an', charges: 'Charges (€)', property_tax: 'Taxe foncière (€)', fees: 'Honoraires',
  owner_name: 'Propriétaire', agency_name: 'Agence', sales_name: 'Commercial', contact_email: 'Email contact', contact_phone: 'Téléphone contact', source_url: 'URL source', description: 'Description',
}
const REQUEST_FIELDS = {
  reference: 'Référence', title: 'Intitulé', client_name: 'Client', contact_name: 'Interlocuteur', email: 'Email', phone: 'Téléphone', property_types: 'Types (liste)',
  transaction: 'Transaction', cities: 'Communes (liste)', postal_codes: 'Codes postaux (liste)', departments: 'Départements (liste)', regions: 'Régions (liste)',
  center_label: 'Centre du rayon', radius_km: 'Rayon (km)', surface_min: 'Surface min', surface_max: 'Surface max', budget_max: 'Budget max (€)', budget_per_sqm_max: 'Budget €/m²',
  min_clear_height: 'Hauteur min', min_docks: 'Quais min', requires_hgv_access: 'Accès PL exigé', min_floor_load: 'Résistance sol min', min_power_kva: 'Puissance min', min_parking: 'Parking min',
  desired_date: 'Date souhaitée', priority: 'Priorité', imperatives: 'Critères impératifs (liste)', comments: 'Commentaires',
}
const NUMERIC = /surface|height|count|doors|load|kva|spaces|price|rent|charges|tax|radius|budget|docks|parking|area|latitude|longitude/
const LIST = ['property_types', 'cities', 'postal_codes', 'departments', 'regions', 'imperatives']
const BOOL = ['hgv_access', 'requires_hgv_access']

function toText(k, v) {
  if (v === null || v === undefined) return ''
  if (Array.isArray(v)) return v.join(', ')
  if (typeof v === 'boolean') return v ? 'oui' : 'non'
  return String(v)
}
function fromText(k, s) {
  if (s === '') return undefined
  if (LIST.includes(k)) return s.split(/[,;]+/).map((x) => x.trim()).filter(Boolean)
  if (BOOL.includes(k)) return /^(oui|true|1|o)$/i.test(s.trim()) ? true : /^(non|false|0|n)$/i.test(s.trim()) ? false : undefined
  if (NUMERIC.test(k)) { const n = Number(s.replace(/\s/g, '').replace(',', '.')); return Number.isFinite(n) ? n : s }
  return s
}

export default function Imports() {
  const toast = useToast()
  const [target, setTarget] = useState('property')
  const [batch, setBatch] = useState(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const list = useApi(() => api('/api/imports'), [])

  const upload = async (file) => {
    if (!file) return
    setBusy(true)
    setResult(null)
    const form = new FormData()
    form.append('target', target)
    form.append('file', file)
    try { setBatch(await api('/api/imports', { method: 'POST', form })); list.reload() } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  const setRow = (i, patch) => setBatch({ ...batch, rows: batch.rows.map((r, j) => (j === i ? { ...r, ...patch } : r)) })
  const setVal = (i, k, s) => {
    const data = { ...batch.rows[i].data }
    const v = fromText(k, s)
    if (v === undefined) delete data[k]
    else data[k] = v
    setRow(i, { data })
  }
  const commit = async () => {
    setBusy(true)
    try {
      const res = await api(`/api/imports/${batch.id}/commit`, { method: 'POST', body: batch.rows })
      setResult(res)
      setBatch(null)
      list.reload()
      toast(`${res.created.length} élément(s) créé(s), ${res.merged.length} fusionné(s)`)
    } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }
  const cancel = async () => { await api(`/api/imports/${batch.id}/cancel`, { method: 'POST' }); setBatch(null); list.reload() }
  const fields = batch?.target === 'request' ? REQUEST_FIELDS : PROPERTY_FIELDS

  return (
    <>
      <div className="page-head"><div><h1>Imports</h1><p>Excel, CSV, PDF, Word : extraction structurée puis vérification humaine obligatoire avant enregistrement.</p></div></div>
      {!batch && (
        <div className="card card-body mb stack">
          <div className="row">
            <b>Importer :</b>
            <button className={`chip ${target === 'property' ? 'on' : ''}`} onClick={() => setTarget('property')}>Des offres immobilières</button>
            <button className={`chip ${target === 'request' ? 'on' : ''}`} onClick={() => setTarget('request')}>Des demandes clients</button>
          </div>
          <label className="dropzone">
            <input type="file" hidden accept=".xlsx,.csv,.pdf,.docx,.txt" onChange={(e) => upload(e.target.files[0])} disabled={busy} />
            <Icon name="upload" size={26} />
            <div><b>{busy ? 'Analyse en cours…' : 'Choisir un fichier'}</b></div>
            <div className="small muted">Excel (.xlsx) ou CSV : une ligne par élément, en-têtes reconnus automatiquement · PDF / Word : fiche commerciale ou email de demande (texte). Les macros sont refusées. Les PDF scannés (images) ne sont pas lus.</div>
          </label>
          <div className="small muted">Photos et fiches commerciales d'un bien : ajoutez-les depuis l'onglet « Photos et documents » de l'offre.</div>
        </div>
      )}
      {result && (
        <div className="alert ok mb">
          Import validé : {result.created.length} créé(s), {result.merged.length} fusionné(s).
          {result.errors.length > 0 && <div>Lignes en erreur : {result.errors.map((e) => `ligne ${e.row_number} (${e.error})`).join(' ; ')}</div>}
        </div>
      )}
      {batch && (
        <div className="stack">
          <div className="card card-body row">
            <div style={{ flex: 1 }}><b>{batch.source_name}</b><div className="small muted">{batch.rows.length} élément(s) détecté(s) · {batch.target === 'property' ? 'offres' : 'demandes'} · rien n'est enregistré avant validation</div></div>
            <button className="btn" onClick={cancel}>Annuler l'import</button>
            <button className="btn btn-primary" onClick={commit} disabled={busy}>Valider les lignes « Créer » / « Fusionner »</button>
          </div>
          {batch.warnings?.map((w) => <div key={w} className="alert warn small">{w}</div>)}
          {batch.rows.map((r, i) => (
            <article key={i} className="card card-body" style={r.action === 'ignorer' ? { opacity: 0.7 } : null}>
              <div className="row mb">
                <b>Ligne {r.row_number}</b>
                <select value={r.action} onChange={(e) => setRow(i, { action: e.target.value })} style={{ width: 'auto' }} aria-label="Action">
                  <option value="creer">Créer</option><option value="ignorer">Ignorer</option>
                  {batch.target === 'property' && r.duplicates?.length > 0 && <option value="fusionner">Compléter une offre existante</option>}
                </select>
                {r.action === 'fusionner' && (
                  <select value={r.merge_into || ''} onChange={(e) => setRow(i, { merge_into: e.target.value })} style={{ width: 'auto' }} aria-label="Offre cible">
                    <option value="">Choisir l'offre…</option>{r.duplicates.map((d) => <option key={d.id} value={d.id}>{d.title || d.reference || `#${d.id}`}</option>)}
                  </select>
                )}
                {r.duplicates?.length > 0 && <span className="badge warn">Doublon probable : {r.duplicates.map((d) => d.reasons?.join(', ') || d.title).join(' ; ')}</span>}
              </div>
              {r.warnings?.map((w) => <div key={w} className="alert warn small mb">{w}</div>)}
              <div className="form-grid">
                {Object.entries(fields).filter(([k]) => k in r.data || k !== 'description').map(([k, label]) => (
                  <label key={k} className={`field ${k === 'description' || k === 'comments' ? 'wide' : ''}`}>
                    <span>{label}{k in r.data && <span className="badge teal" style={{ marginLeft: 6 }}>extrait</span>}</span>
                    {k === 'description' || k === 'comments'
                      ? <textarea value={toText(k, r.data[k])} onChange={(e) => setVal(i, k, e.target.value)} />
                      : <input type="text" value={toText(k, r.data[k])} onChange={(e) => setVal(i, k, e.target.value)} placeholder={k === 'property_type' ? Object.keys(TYPE_LABELS).join(' | ') : k === 'imperatives' ? Object.keys(IMPERATIVES).join(', ') : k === 'transaction' ? 'vente | location' : ''} />}
                    {r.evidence?.[k] && <span className="hint">Source : « {r.evidence[k]} »</span>}
                    {!r.evidence?.[k] && r.raw?.[k] && <span className="hint">Valeur d'origine : « {r.raw[k]} »</span>}
                  </label>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
      <section className="card mt">
        <div className="card-head"><h2>Imports récents</h2></div>
        <Loader state={list}>{(l) => !l.length ? <div className="card-body muted small">Aucun import.</div> : (
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Fichier</th><th>Cible</th><th>Lignes</th><th>Statut</th><th>Date</th><th></th></tr></thead>
            <tbody>{l.map((b) => (
              <tr key={b.id}>
                <td>{b.source_name}</td><td>{b.target === 'property' ? 'Offres' : 'Demandes'}</td><td>{b.row_count}</td>
                <td><span className={`badge ${b.status === 'valide' ? 'ok' : b.status === 'annule' ? '' : 'warn'}`}>{{ a_valider: 'À valider', valide: 'Validé', annule: 'Annulé' }[b.status]}</span></td>
                <td>{dateTime(b.created_at)}</td>
                <td>{b.status === 'a_valider' && <button className="btn btn-sm" onClick={async () => setBatch(await api(`/api/imports/${b.id}`))}>Reprendre</button>}{b.document_id && <a className="btn btn-sm btn-ghost" href={`/api/files/${b.document_id}?download=true`}>Fichier</a>}</td>
              </tr>))}
            </tbody>
          </table></div>
        )}</Loader>
      </section>
      <p className="small muted mt">Après validation, retrouvez les éléments dans <Link to="/offres?source_kind=import">les offres importées</Link> ou <Link to="/demandes">les demandes</Link>.</p>
    </>
  )
}
