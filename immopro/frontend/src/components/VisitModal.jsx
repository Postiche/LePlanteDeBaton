import { useState } from 'react'
import { api } from '../api.js'
import EmailComposer from './EmailComposer.jsx'
import Icon from './Icon.jsx'
import { Field, Modal, useToast } from './ui.jsx'

// Proposer une visite : plusieurs créneaux, puis génération de l'email de proposition.
export default function VisitModal({ propertyId, requestId, contactId, matchId, onClose, onDone }) {
  const toast = useToast()
  const [slots, setSlots] = useState([''])
  const [notes, setNotes] = useState('')
  const [visit, setVisit] = useState(null)
  const create = async () => {
    const proposed = slots.filter(Boolean)
    try {
      const v = await api('/api/visits', { method: 'POST', body: { property_id: propertyId, request_id: requestId, contact_id: contactId, match_id: matchId, proposed_slots: proposed, notes } })
      setVisit(v)
      onDone && onDone()
    } catch (e) { toast(e.message, 'error') }
  }
  if (visit) {
    return <EmailComposer context={{ template: 'proposition_visite', property_ids: [propertyId], request_id: requestId, contact_id: visit.contact_id, match_id: matchId, visit_id: visit.id }} onClose={onClose} />
  }
  return (
    <Modal title="Proposer une visite" onClose={onClose} footer={<><button className="btn" onClick={onClose}>Annuler</button><button className="btn btn-primary" onClick={create}>Enregistrer et préparer l'email</button></>}>
      <div className="stack">
        <p className="muted small" style={{ margin: 0 }}>Indiquez un ou plusieurs créneaux. La visite restera « proposée » tant que le client n'a pas confirmé un créneau : la confirmation se saisit manuellement.</p>
        {slots.map((s, i) => (
          <div className="row" key={i}>
            <input type="datetime-local" value={s} onChange={(e) => setSlots(slots.map((x, j) => (j === i ? e.target.value : x)))} style={{ flex: 1 }} aria-label={`Créneau ${i + 1}`} />
            {slots.length > 1 && <button className="icon-btn" onClick={() => setSlots(slots.filter((_, j) => j !== i))} aria-label="Retirer"><Icon name="x" size={18} /></button>}
          </div>
        ))}
        {slots.length < 6 && <button className="btn btn-sm" onClick={() => setSlots([...slots, ''])}><Icon name="plus" />Ajouter un créneau</button>}
        <Field label="Notes internes"><textarea value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      </div>
    </Modal>
  )
}
