import { useNavigate } from 'react-router-dom'
import { PROPERTY_STATUS, TRANSACTION_LABELS, TYPE_LABELS, num, priceLabel, propertyLabel } from '../format.js'
import Icon from './Icon.jsx'
import { DemoBadge } from './ui.jsx'

export default function PropertyCard({ p, extra }) {
  const nav = useNavigate()
  return (
    <article className="card prop-card" onClick={() => nav(`/offres/${p.id}`)}>
      <div className="prop-photo">
        {p.cover_photo_id ? <img src={`/api/files/${p.cover_photo_id}`} alt="" loading="lazy" /> : <Icon name="building" size={40} />}
        <div className="tags">
          {p.transaction && <span className="badge navy">{TRANSACTION_LABELS[p.transaction]}</span>}
          {p.status !== 'active' && <span className="badge warn">{PROPERTY_STATUS[p.status]}</span>}
          {p.source_kind === 'externe' && <span className="badge">Externe</span>}
          <DemoBadge show={p.is_demo} />
        </div>
      </div>
      <div className="card-body">
        <div className="small muted">{TYPE_LABELS[p.property_type] || 'Type non renseigné'}{p.reference ? ` · ${p.reference}` : ''}</div>
        <h3>{propertyLabel(p)}</h3>
        <div className="small" style={{ color: 'var(--text-2)' }}><Icon name="pin" size={13} /> {[p.postal_code, p.city].filter(Boolean).join(' ') || 'Localisation non renseignée'}</div>
        <div className="facts">
          <span><b>{num(p.surface_total, 'm²')}</b></span>
          {p.clear_height && <span>H. {num(p.clear_height, 'm')}</span>}
          {p.dock_count != null && <span>{p.dock_count} quais</span>}
        </div>
        <div className="spacer" />
        <div className="price">{priceLabel(p)}</div>
        {extra}
      </div>
    </article>
  )
}
