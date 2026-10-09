export const TYPE_LABELS = {
  entrepot: 'Entrepôt', plateforme_logistique: 'Plateforme logistique', local_activite: "Local d'activité",
  batiment_industriel: 'Bâtiment industriel', bureaux: 'Bureaux', terrain: 'Terrain', commerce: 'Commerce', autre: 'Autre',
}
export const TRANSACTION_LABELS = { vente: 'Vente', location: 'Location', vente_ou_location: 'Vente ou location' }
export const PROPERTY_STATUS = { active: 'Active', sous_offre: 'Sous offre', vendue_louee: 'Vendue / louée', archivee: 'Archivée' }
export const REQUEST_STATUS = { active: 'Active', en_pause: 'En pause', satisfaite: 'Satisfaite', abandonnee: 'Abandonnée' }
export const PRIORITIES = { basse: 'Basse', normale: 'Normale', haute: 'Haute', urgente: 'Urgente' }
export const PIPELINE = {
  a_contacter: 'À contacter', email_prepare: 'Email préparé', contacte: 'Contacté', en_attente: 'En attente de réponse',
  visite_proposee: 'Visite proposée', visite_confirmee: 'Visite confirmée', visite_effectuee: 'Visite effectuée',
  negociation: 'Négociation', sans_suite: 'Sans suite',
}
export const VISIT_STATUS = { proposee: 'Proposée', confirmee: 'Confirmée', effectuee: 'Effectuée', annulee: 'Annulée' }
export const CONTACT_KINDS = { client: 'Client', proprietaire: 'Propriétaire', agence: 'Agence', commercial: 'Commercial', partenaire: 'Partenaire', annonceur: 'Annonceur', autre: 'Autre' }
export const COMPANY_KINDS = { client: 'Client', proprietaire: 'Propriétaire', agence: 'Agence', partenaire: 'Partenaire', autre: 'Autre' }
export const INTERACTION_KINDS = {
  appel: 'Appel', email_prepare: 'Email préparé', email_envoye: 'Email envoyé', rendez_vous: 'Rendez-vous', visite: 'Visite',
  note: 'Note', relance: 'Relance', compte_rendu: 'Compte rendu', statut: 'Changement de statut',
}
export const IMPERATIVES = {
  localisation: 'Localisation', surface: 'Surface', budget: 'Budget', typologie: 'Type de bien', transaction: 'Transaction',
  hauteur_libre: 'Hauteur libre', quais: 'Quais', acces_pl: 'Accès poids lourds', resistance_sol: 'Résistance au sol',
  puissance: 'Puissance électrique', parking: 'Parking', disponibilite: 'Disponibilité',
}
export const REGIONS = [
  'Auvergne-Rhône-Alpes', 'Bourgogne-Franche-Comté', 'Bretagne', 'Centre-Val de Loire', 'Corse', 'Grand Est', 'Hauts-de-France',
  'Île-de-France', 'Normandie', 'Nouvelle-Aquitaine', 'Occitanie', 'Pays de la Loire', "Provence-Alpes-Côte d'Azur",
  'Guadeloupe', 'Martinique', 'Guyane', 'La Réunion', 'Mayotte',
]

const nf = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 })
export const num = (v, unit = '') => (v === null || v === undefined || v === '' ? '—' : `${nf.format(v)}${unit ? ' ' + unit : ''}`)
export const eur = (v) => (v === null || v === undefined ? '—' : `${nf.format(Math.round(v))} €`)
export const date = (v) => (v ? new Date(v.length === 10 ? v + 'T00:00:00' : v).toLocaleDateString('fr-FR') : '—')
// Horodatages système stockés en UTC (sans suffixe) : on les interprète comme UTC.
const asUtc = (v) => (typeof v === 'string' && /T\d\d:\d\d/.test(v) && !/([zZ]|[+-]\d\d:\d\d)$/.test(v) ? v + 'Z' : v)
export const dateTime = (v) => (v ? new Date(asUtc(v)).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '—')
// Créneaux de visite : heure locale « murale » saisie par l'utilisateur (pas de conversion).
export const slot = (v) => (v ? new Date(v).toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—')
// Valeur d'un champ datetime-local (heure locale) → ISO UTC sans suffixe pour l'API.
export const localToUtc = (v) => (v ? new Date(v).toISOString().slice(0, 19) : null)
export const yesNo = (v) => (v === true ? 'Oui' : v === false ? 'Non' : '—')

export function priceLabel(p) {
  if (p.sale_price) return eur(p.sale_price)
  if (p.annual_rent) return `${eur(p.annual_rent)} /an`
  if (p.rent_per_sqm) return `${num(p.rent_per_sqm)} €/m²/an`
  return 'Prix non renseigné'
}

export function propertyLabel(p) {
  return p.title || [TYPE_LABELS[p.property_type], p.city].filter(Boolean).join(' – ') || p.reference || `Offre #${p.id}`
}

export function requestLabel(r) {
  return r.title || r.reference || r.display_client || r.client_name || `Demande #${r.id}`
}

export function telHref(phone) {
  return 'tel:' + String(phone).replace(/[^\d+]/g, '')
}
