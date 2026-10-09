import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, download } from '../api.js'
import { useAuth } from '../auth.jsx'
import ContactCard from '../components/ContactCard.jsx'
import Documents from '../components/Documents.jsx'
import EmailComposer from '../components/EmailComposer.jsx'
import Icon from '../components/Icon.jsx'
import MapView from '../components/MapView.jsx'
import MatchExplain from '../components/MatchExplain.jsx'
import Timeline from '../components/Timeline.jsx'
import VisitModal from '../components/VisitModal.jsx'
import { DemoBadge, Dl, Loader, Modal, Score, useApi, useToast } from '../components/ui.jsx'
import { PIPELINE, PROPERTY_STATUS, TRANSACTION_LABELS, TYPE_LABELS, date, dateTime, eur, num, propertyLabel, yesNo } from '../format.js'

export default function PropertyDetail() {
  const { id } = useParams()
  const toast = useToast()
  const { can } = useAuth()
  const st = useApi(() => api(`/api/properties/${id}`), [id])
  const [tab, setTab] = useState('fiche')
  const [modal, setModal] = useState(null)

  const act = async (fn, msg) => { try { await fn(); toast(msg); st.reload() } catch (e) { toast(e.message, 'error') } }

  return (
    <Loader state={st}>{(p) => (
      <>
        <div className="page-head">
          <div>
            <div className="row small muted">
              <Link to="/offres">Offres</Link> › {p.reference || `#${p.id}`}
              <DemoBadge show={p.is_demo} />
              <span className={`badge ${p.status === 'active' ? 'ok' : 'warn'}`}>{PROPERTY_STATUS[p.status]}</span>
              {p.transaction && <span className="badge navy">{TRANSACTION_LABELS[p.transaction]}</span>}
            </div>
            <h1 style={{ marginTop: 6 }}>{propertyLabel(p)}</h1>
            <p>{[p.address, [p.postal_code, p.city].filter(Boolean).join(' ')].filter(Boolean).join(', ') || 'Adresse non renseignée'}</p>
          </div>
          <div className="row">
            <button className="btn" onClick={() => download(`/api/properties/${p.id}/pdf`)}><Icon name="file" />Fiche PDF</button>
            {can('write') && <>
              <button className="btn" onClick={() => setModal({ type: 'visit' })}><Icon name="calendar" />Proposer une visite</button>
              <Link className="btn" to={`/offres/${p.id}/modifier`}><Icon name="edit" />Modifier</Link>
              {p.status === 'archivee'
                ? <button className="btn" onClick={() => act(() => api(`/api/properties/${p.id}/restore`, { method: 'POST' }), 'Offre restaurée')}>Restaurer</button>
                : <button className="btn" onClick={() => act(() => api(`/api/properties/${p.id}/archive`, { method: 'POST' }), 'Offre archivée')}><Icon name="archive" />Archiver</button>}
            </>}
          </div>
        </div>
        {p.duplicates?.length > 0 && (
          <div className="alert warn mb">Doublon(s) probable(s) : {p.duplicates.map((d, i) => <span key={d.id}>{i > 0 && ', '}<Link to={`/offres/${d.id}`}>{d.title || d.reference || `#${d.id}`}</Link> ({d.reasons.join(', ')})</span>)}</div>
        )}
        <div className="tabs" role="tablist">
          {[['fiche', 'Fiche'], ['documents', `Photos et documents (${p.documents.length})`], ['clients', 'Clients correspondants'], ['contacts', 'Contacts'], ['historique', 'Historique']].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
        {tab === 'fiche' && (
          <div className="split">
            <div className="stack">
              {p.cover_photo_id && <img src={`/api/files/${p.cover_photo_id}`} alt="" style={{ width: '100%', maxHeight: 380, objectFit: 'cover', borderRadius: 12 }} />}
              <section className="card card-body">
                <h2 className="mb">Caractéristiques</h2>
                <div className="grid g2">
                  <Dl rows={[
                    ['Type', TYPE_LABELS[p.property_type]], ['Surface totale', p.surface_total && num(p.surface_total, 'm²')],
                    ['Divisible dès', p.surface_divisible_min && num(p.surface_divisible_min, 'm²')], ['Stockage / activité', p.surface_storage && num(p.surface_storage, 'm²')],
                    ['Bureaux', p.surface_offices && num(p.surface_offices, 'm²')], ['Terrain', p.land_area && num(p.land_area, 'm²')],
                    ['Hauteur libre', p.clear_height && num(p.clear_height, 'm')], ['Quais', p.dock_count], ['Portes sectionnelles', p.sectional_doors],
                  ]} />
                  <Dl rows={[
                    ['Accès poids lourds', p.hgv_access == null ? null : yesNo(p.hgv_access)], ['Résistance au sol', p.floor_load && num(p.floor_load, 't/m²')],
                    ['Puissance', p.power_kva && num(p.power_kva, 'kVA')], ['Parking', p.parking_spaces != null ? `${p.parking_spaces} places` : null],
                    ['État', p.condition], ['Disponibilité', p.available_from ? date(p.available_from) : p.availability_note],
                    ['Département', p.department], ['Région', p.region],
                  ]} />
                </div>
              </section>
              <section className="card card-body">
                <h2 className="mb">Conditions financières</h2>
                <Dl rows={[
                  ['Prix de vente', p.sale_price && eur(p.sale_price)], ['Loyer annuel HT HC', p.annual_rent && eur(p.annual_rent)],
                  ['Loyer au m²', p.rent_per_sqm && `${num(p.rent_per_sqm)} €/m²/an`], ['Charges', p.charges && eur(p.charges)],
                  ['Taxe foncière', p.property_tax && eur(p.property_tax)], ['Honoraires', p.fees],
                ]} />
              </section>
              {p.description && <section className="card card-body"><h2 className="mb">Description</h2><div style={{ whiteSpace: 'pre-wrap' }}>{p.description}</div></section>}
            </div>
            <div className="stack">
              <section className="card card-body">
                <h2 className="mb">Localisation</h2>
                {p.latitude != null ? <MapView small points={[{ ...p, lat: p.latitude, lon: p.longitude }]} /> : (
                  <div className="alert warn small">Adresse non géocodée{p.geocode_status === 'echec' ? ' (échec du géocodage)' : ''} : le bien n'apparaît pas sur la carte et la distance au rayon de recherche ne peut pas être calculée.
                    {can('write') && <div className="mt"><button className="btn btn-sm" onClick={() => act(() => api(`/api/properties/${p.id}/geocode`, { method: 'POST' }), 'Adresse géocodée')}>Géocoder l'adresse</button></div>}
                  </div>
                )}
                {p.geocode_status === 'auto' && <div className="small muted mt">Position géocodée automatiquement — à vérifier.</div>}
              </section>
              <ContactCard title="Commercial" contact={p.sales_contact} onEmail={() => setModal({ type: 'email', ctx: { template: 'presentation_bien', property_ids: [p.id] } })} />
              <section className="card card-body small">
                <h3 className="mb">Provenance</h3>
                <Dl rows={[
                  ['Origine', { manuel: 'Saisie manuelle', import: 'Import de fichier', externe: 'Annonce externe' }[p.source_kind]],
                  ['Source', p.source_name], ['Référence source', p.source_ref],
                  ['URL', p.source_url && <a href={p.source_url} target="_blank" rel="noreferrer noopener">Ouvrir l'annonce <Icon name="external" size={12} /></a>],
                  ['Consultée le', p.source_consulted_at && dateTime(p.source_consulted_at)], ['Créée le', dateTime(p.created_at)], ['Modifiée le', dateTime(p.updated_at)],
                ]} />
              </section>
            </div>
          </div>
        )}
        {tab === 'documents' && <section className="card card-body"><Documents ownerType="property" ownerId={p.id} documents={p.documents} onChange={st.reload} /></section>}
        {tab === 'clients' && <PropertyClients property={p} setModal={setModal} />}
        {tab === 'contacts' && (
          <div className="grid g3">
            <ContactCard title="Commercial" contact={p.sales_contact} onEmail={p.sales_contact ? () => setModal({ type: 'email', ctx: { template: 'relance', contact_id: p.sales_contact.id, property_ids: [p.id] } }) : null} />
            <ContactCard title="Agence / annonceur" contact={p.agency_contact} onEmail={p.agency_contact ? () => setModal({ type: 'email', ctx: { template: 'demande_info_annonceur', contact_id: p.agency_contact.id, property_ids: [p.id] } }) : null} />
            <ContactCard title="Propriétaire" contact={p.owner_contact} onEmail={p.owner_contact ? () => setModal({ type: 'email', ctx: { template: 'relance', contact_id: p.owner_contact.id, property_ids: [p.id] } }) : null} />
          </div>
        )}
        {tab === 'historique' && <section className="card card-body"><Timeline params={{ property_id: p.id }} link={{ property_id: p.id }} /></section>}
        {modal?.type === 'email' && <EmailComposer context={modal.ctx} onClose={() => setModal(null)} />}
        {modal?.type === 'visit' && <VisitModal propertyId={p.id} requestId={modal.requestId} matchId={modal.matchId} onClose={() => setModal(null)} />}
        {modal?.type === 'explain' && <Modal title={`Score ${modal.result.score}/100`} onClose={() => setModal(null)}><MatchExplain result={modal.result} /></Modal>}
      </>
    )}</Loader>
  )
}

function PropertyClients({ property, setModal }) {
  const [elim, setElim] = useState(false)
  const st = useApi(() => api(`/api/properties/${property.id}/matches`, { params: { include_eliminated: elim } }), [property.id, elim])
  return (
    <div className="stack">
      <div className="row"><span className="muted small">Calcul en direct sur toutes les demandes actives.</span><div className="spacer" /><label className="check"><input type="checkbox" checked={elim} onChange={(e) => setElim(e.target.checked)} />Afficher les demandes éliminées</label></div>
      <Loader state={st}>{(list) => !list.length ? <div className="empty">Aucune demande active compatible.</div> : list.map((m) => (
        <article key={m.request.id} className="card card-body" style={m.eliminated ? { opacity: 0.65 } : null}>
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <Score value={m.score} />
            <div style={{ flex: 1, minWidth: 220 }}>
              <Link to={`/demandes/${m.request.id}`}><h3>{m.request.title || m.request.reference || 'Demande'}</h3></Link>
              <div className="small muted">{m.request.client_name}{m.status ? ` · ${PIPELINE[m.status]}` : ''}</div>
              {m.eliminated && <span className="badge danger">Éliminée : {m.eliminated_by[0]}</span>}
              <div className="small mt">{m.satisfied.slice(0, 3).join(' · ')}</div>
              {m.missing.length > 0 && <div className="small muted">À vérifier : {m.missing.slice(0, 3).join(' · ')}</div>}
            </div>
            <div className="row">
              <button className="btn btn-sm" onClick={() => setModal({ type: 'explain', result: m })}>Détail du score</button>
              <button className="btn btn-sm" onClick={() => setModal({ type: 'email', ctx: { template: 'presentation_bien', property_ids: [property.id], request_id: m.request.id, match_id: m.match_id } })}><Icon name="mail" />Email</button>
              <button className="btn btn-sm" onClick={() => setModal({ type: 'visit', requestId: m.request.id, matchId: m.match_id })}><Icon name="calendar" />Visite</button>
            </div>
          </div>
          <div className="mt"><ContactCardInline m={m} /></div>
        </article>
      ))}</Loader>
    </div>
  )
}

function ContactCardInline({ m }) {
  const c = m.request.contact
  const fallback = !c && (m.request.contact_name || m.request.email || m.request.phone) ? { display_name: m.request.contact_name, email: m.request.email, phone: m.request.phone, company_name: m.request.client_name } : null
  return <ContactCard title="Client" contact={c} fallback={fallback} />
}
