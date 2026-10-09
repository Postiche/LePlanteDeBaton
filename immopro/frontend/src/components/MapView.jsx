import L from 'leaflet'
import { useEffect, useRef } from 'react'
import { useAuth } from '../auth.jsx'

const pin = (color) => L.divIcon({
  className: '',
  html: `<svg width="28" height="38" viewBox="0 0 28 38"><path d="M14 0C6.3 0 0 6.2 0 13.9 0 24.3 14 38 14 38s14-13.7 14-24.1C28 6.2 21.7 0 14 0z" fill="${color}"/><circle cx="14" cy="14" r="5.5" fill="#fff"/></svg>`,
  iconSize: [28, 38], iconAnchor: [14, 38], popupAnchor: [0, -34],
})
const ICONS = { default: pin('#0B1F3A'), highlight: pin('#0D9488'), demo: pin('#B7791F') }

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

// Carte Leaflet / OpenStreetMap. Les popups n'affichent jamais de coordonnées de contact.
export default function MapView({ points = [], circles = [], onSelect, small, highlight }) {
  const el = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)
  const { settings } = useAuth()
  useEffect(() => {
    map.current = L.map(el.current, { scrollWheelZoom: !small }).setView([46.6, 2.4], 6)
    L.tileLayer(settings?.map_tile_url || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: settings?.map_attribution || '© contributeurs OpenStreetMap',
    }).addTo(map.current)
    layer.current = L.layerGroup().addTo(map.current)
    return () => map.current.remove()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    const g = layer.current
    g.clearLayers()
    const bounds = []
    circles.forEach((c) => {
      L.circle([c.lat, c.lon], { radius: c.radius_km * 1000, color: '#0D9488', weight: 2, fillOpacity: 0.08 }).addTo(g).bindTooltip(c.label || 'Zone de recherche')
      bounds.push([c.lat, c.lon])
    })
    points.forEach((p) => {
      const icon = highlight?.includes(p.id) ? ICONS.highlight : p.is_demo ? ICONS.demo : ICONS.default
      const m = L.marker([p.lat, p.lon], { icon }).addTo(g)
      m.bindPopup(`<b>${esc(p.title || p.reference || 'Offre')}</b><br>${esc([p.postal_code, p.city].filter(Boolean).join(' '))}<br>${p.surface_total ? esc(new Intl.NumberFormat('fr-FR').format(p.surface_total) + ' m²') : ''}${p.geocode_status === 'auto' ? '<br><small>Position géocodée automatiquement</small>' : ''}<br><a href="/offres/${p.id}" data-id="${p.id}">Voir la fiche</a>`)
      m.on('popupopen', (e) => {
        const a = e.popup.getElement().querySelector('a[data-id]')
        if (a && onSelect) a.onclick = (ev) => { ev.preventDefault(); onSelect(p.id) }
      })
      bounds.push([p.lat, p.lon])
    })
    if (bounds.length === 1) map.current.setView(bounds[0], 11)
    else if (bounds.length > 1) map.current.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 })
  }, [points, circles, highlight, onSelect])
  return <div ref={el} className={`map ${small ? 'small' : ''}`} />
}
