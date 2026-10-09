import { Link } from 'react-router-dom'
import { CONTACT_KINDS, telHref } from '../format.js'
import Icon from './Icon.jsx'
import { useToast } from './ui.jsx'

// Affiche uniquement les coordonnées réellement disponibles et les actions associées.
export default function ContactCard({ contact, title, onEmail, onVisit, fallback }) {
  const toast = useToast()
  const c = contact || fallback
  if (!c) return <div className="contact-card"><div className="muted small">{title ? `${title} : ` : ''}aucune coordonnée renseignée.</div></div>
  const name = c.display_name || [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name
  const phone = c.mobile || c.phone
  const lines = [
    name && `${c.civility ? c.civility + ' ' : ''}${name}`,
    c.job_title,
    c.company_name,
    c.email,
    c.phone,
    c.mobile && c.mobile !== c.phone ? c.mobile : null,
    c.address,
  ].filter(Boolean)
  const copy = async () => {
    try { await navigator.clipboard.writeText(lines.join('\n')); toast('Coordonnées copiées') } catch { toast('Copie impossible sur ce navigateur', 'error') }
  }
  return (
    <div className="contact-card">
      <div className="row">
        {title && <span className="badge">{title}</span>}
        {c.kind && <span className="badge teal">{CONTACT_KINDS[c.kind] || c.kind}</span>}
        {c.is_public_listing_contact && <span className="badge" title="Coordonnées publiques issues d'une annonce">Annonce publique</span>}
        {c.opposed_to_prospecting && <span className="badge danger" title="Opposition à la prospection commerciale">Opposé à la prospection</span>}
        {c.is_demo && <span className="badge demo">DÉMO</span>}
      </div>
      {name && <div className="name">{c.id && c.kind ? <Link to={`/contacts/${c.id}`}>{name}</Link> : name}</div>}
      <div className="small" style={{ color: 'var(--text-2)' }}>
        {[c.job_title, c.company_name].filter(Boolean).join(' · ')}
        {c.email && <div><a href={`mailto:${c.email}`}>{c.email}</a></div>}
        {c.phone && <div><a href={telHref(c.phone)}>{c.phone}</a></div>}
        {c.mobile && c.mobile !== c.phone && <div><a href={telHref(c.mobile)}>{c.mobile}</a></div>}
        {c.origin && <div className="muted">Origine : {c.origin}</div>}
      </div>
      <div className="actions">
        <button className="btn btn-sm" onClick={copy}><Icon name="copy" />Copier</button>
        {phone && <a className="btn btn-sm" href={telHref(phone)}><Icon name="phone" />Appeler</a>}
        {onEmail && <button className="btn btn-sm" onClick={onEmail}><Icon name="mail" />Préparer un email</button>}
        {onVisit && <button className="btn btn-sm" onClick={onVisit}><Icon name="calendar" />Proposer une visite</button>}
      </div>
    </div>
  )
}
