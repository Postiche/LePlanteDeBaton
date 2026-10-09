import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, download } from '../api.js'
import Icon from '../components/Icon.jsx'
import PropertyCard from '../components/PropertyCard.jsx'
import { DemoBadge, Empty, Field, Loader, useApi } from '../components/ui.jsx'
import { PROPERTY_STATUS, TRANSACTION_LABELS, TYPE_LABELS, num, priceLabel, propertyLabel } from '../format.js'

const FILTERS = ['q', 'property_type', 'transaction', 'status', 'city', 'department', 'surface_min', 'surface_max', 'price_max', 'rent_max', 'min_height', 'min_docks', 'hgv', 'geocoded', 'source_kind', 'demo', 'sort']

export default function Properties() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const [view, setView] = useState(() => { try { return localStorage.getItem('immopro_view') || 'cards' } catch { return 'cards' } })
  const [showFilters, setShowFilters] = useState(false)
  const params = Object.fromEntries(FILTERS.map((k) => [k, sp.get(k) || '']))
  const page = +(sp.get('page') || 1)
  const st = useApi(() => api('/api/properties', { params: { ...params, status: params.status || 'actives', page, page_size: 48 } }), [sp.toString()])
  const setF = (k, v) => { const n = new URLSearchParams(sp); if (v === '' || v == null) n.delete(k); else n.set(k, v); n.delete('page'); setSp(n, { replace: true }) }
  const changeView = (v) => { setView(v); try { localStorage.setItem('immopro_view', v) } catch { /* stockage indisponible */ } }
  const input = (k, label, type = 'number', ph) => (
    <Field label={label}><input type={type} inputMode={type === 'number' ? 'decimal' : undefined} value={params[k]} placeholder={ph} onChange={(e) => setF(k, e.target.value)} /></Field>
  )
  return (
    <>
      <div className="page-head">
        <div><h1>Offres immobilières</h1><p>{st.data ? `${st.data.total} offre(s)` : 'Chargement…'}</p></div>
        <div className="row">
          <button className="btn" onClick={() => setShowFilters(!showFilters)}><Icon name="search" />Filtres avancés</button>
          <button className="btn" onClick={() => download('/api/exports/offres.xlsx')}><Icon name="download" />Excel</button>
          <button className="btn" onClick={() => download('/api/exports/offres.csv')}>CSV</button>
          <Link className="btn btn-accent" to="/offres/nouvelle"><Icon name="plus" />Nouvelle offre</Link>
        </div>
      </div>
      <div className="card card-body mb">
        <div className="form-grid">
          <Field label="Recherche"><input type="search" value={params.q} onChange={(e) => setF('q', e.target.value)} placeholder="Réf., ville, adresse, description" /></Field>
          <Field label="Type de bien"><select value={params.property_type} onChange={(e) => setF('property_type', e.target.value)}><option value="">Tous</option>{Object.entries(TYPE_LABELS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
          <Field label="Transaction"><select value={params.transaction} onChange={(e) => setF('transaction', e.target.value)}><option value="">Toutes</option><option value="vente">Vente</option><option value="location">Location</option></select></Field>
          <Field label="Statut"><select value={params.status} onChange={(e) => setF('status', e.target.value)}><option value="">Actives et sous offre</option>{Object.entries(PROPERTY_STATUS).map(([k, l]) => <option key={k} value={k}>{l}</option>)}<option value="toutes">Toutes</option></select></Field>
          {input('surface_min', 'Surface min (m²)')}
          {input('surface_max', 'Surface max (m²)')}
        </div>
        {showFilters && (
          <div className="form-grid mt">
            {input('city', 'Ville', 'text')}
            {input('department', 'Départements', 'text', 'ex. 69,38')}
            {input('price_max', 'Prix de vente max (€)')}
            {input('rent_max', 'Loyer annuel max (€)')}
            {input('min_height', 'Hauteur libre min (m)')}
            {input('min_docks', 'Quais min')}
            <Field label="Accès poids lourds"><select value={params.hgv} onChange={(e) => setF('hgv', e.target.value)}><option value="">Indifférent</option><option value="true">Oui</option><option value="false">Non</option></select></Field>
            <Field label="Géolocalisation"><select value={params.geocoded} onChange={(e) => setF('geocoded', e.target.value)}><option value="">Toutes</option><option value="true">Géolocalisées</option><option value="false">Non géocodées</option></select></Field>
            <Field label="Origine"><select value={params.source_kind} onChange={(e) => setF('source_kind', e.target.value)}><option value="">Toutes</option><option value="manuel">Saisie</option><option value="import">Import</option><option value="externe">Annonce externe</option></select></Field>
            <Field label="Données"><select value={params.demo} onChange={(e) => setF('demo', e.target.value)}><option value="">Toutes</option><option value="real">Réelles</option><option value="demo">Démonstration</option></select></Field>
            <Field label="Tri"><select value={params.sort} onChange={(e) => setF('sort', e.target.value)}><option value="">Dernières modifiées</option><option value="-created_at">Plus récentes</option><option value="surface_total">Surface croissante</option><option value="-surface_total">Surface décroissante</option><option value="annual_rent">Loyer croissant</option><option value="sale_price">Prix croissant</option><option value="city">Ville</option></select></Field>
          </div>
        )}
        <div className="row mt">
          <button className="btn btn-sm btn-ghost" onClick={() => setSp(new URLSearchParams(), { replace: true })}>Réinitialiser</button>
          <div className="spacer" />
          <button className={`btn btn-sm ${view === 'cards' ? 'btn-primary' : ''}`} onClick={() => changeView('cards')}>Fiches</button>
          <button className={`btn btn-sm ${view === 'table' ? 'btn-primary' : ''}`} onClick={() => changeView('table')}>Tableau</button>
        </div>
      </div>
      <Loader state={st}>{(d) => !d.items.length ? <Empty icon="building">Aucune offre ne correspond à ces critères.</Empty> : (
        <>
          {view === 'cards' ? (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>{d.items.map((p) => <PropertyCard key={p.id} p={p} />)}</div>
          ) : (
            <div className="card table-wrap">
              <table className="table">
                <thead><tr><th>Réf.</th><th>Bien</th><th>Localisation</th><th className="right">Surface</th><th className="right">Prix / loyer</th><th className="hide-sm">Hauteur</th><th className="hide-sm">Quais</th><th className="hide-sm">Origine</th></tr></thead>
                <tbody>{d.items.map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => nav(`/offres/${p.id}`)}>
                    <td className="nowrap">{p.reference || '—'} <DemoBadge show={p.is_demo} /></td>
                    <td><b>{propertyLabel(p)}</b><div className="small muted">{TYPE_LABELS[p.property_type] || '—'} · {TRANSACTION_LABELS[p.transaction] || '—'}</div></td>
                    <td>{[p.postal_code, p.city].filter(Boolean).join(' ') || '—'}</td>
                    <td className="right nowrap">{num(p.surface_total, 'm²')}</td>
                    <td className="right nowrap">{priceLabel(p)}</td>
                    <td className="hide-sm">{num(p.clear_height, 'm')}</td>
                    <td className="hide-sm">{p.dock_count ?? '—'}</td>
                    <td className="hide-sm small">{p.source_name || p.source_kind}</td>
                  </tr>))}
                </tbody>
              </table>
            </div>
          )}
          {d.total > d.page_size && (
            <div className="row mt" style={{ justifyContent: 'center' }}>
              <button className="btn btn-sm" disabled={page <= 1} onClick={() => { const n = new URLSearchParams(sp); n.set('page', page - 1); setSp(n) }}>Précédent</button>
              <span className="small">Page {page} / {Math.ceil(d.total / d.page_size)}</span>
              <button className="btn btn-sm" disabled={page * d.page_size >= d.total} onClick={() => { const n = new URLSearchParams(sp); n.set('page', page + 1); setSp(n) }}>Suivant</button>
            </div>
          )}
        </>
      )}</Loader>
    </>
  )
}
