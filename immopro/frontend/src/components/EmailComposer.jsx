import { useEffect, useState } from 'react'
import { api, download } from '../api.js'
import { useAuth } from '../auth.jsx'
import Icon from './Icon.jsx'
import { Field, Modal, useToast } from './ui.jsx'

const TEMPLATES = {
  presentation_bien: "Présentation d'un bien",
  selection_biens: 'Sélection de plusieurs biens',
  proposition_visite: 'Proposition de visite',
  demande_info_annonceur: "Demande d'informations à un annonceur",
  relance: 'Relance',
  compte_rendu: 'Compte rendu',
}

export function outlookToken() {
  try { return localStorage.getItem('immopro_outlook_token') || '' } catch { return '' }
}

// Éditeur d'emails : aucun message n'est jamais envoyé automatiquement par l'application.
export default function EmailComposer({ context, onClose, onDone }) {
  const { settings, can } = useAuth()
  const toast = useToast()
  const [template, setTemplate] = useState(context.template || 'presentation_bien')
  const [mail, setMail] = useState(null)
  const [draftId, setDraftId] = useState(null)
  const [status, setStatus] = useState(null)
  const [attach, setAttach] = useState(true)
  const [confirmSent, setConfirmSent] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    api('/api/emails/compose', { method: 'POST', body: { ...context, template } })
      .then((m) => alive && setMail(m))
      .catch((e) => toast(e.message, 'error'))
    setDraftId(null)
    setStatus(null)
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template])

  const set = (k) => (e) => setMail({ ...mail, [k]: e.target.value })

  const saveDraft = async () => {
    const payload = {
      template, to_email: mail.to_email, cc: mail.cc, subject: mail.subject, body: mail.body,
      contact_id: mail.contact_id, request_id: mail.request_id, property_ids: mail.property_ids, match_id: mail.match_id, visit_id: mail.visit_id,
    }
    if (draftId) { await api(`/api/emails/drafts/${draftId}`, { method: 'PUT', body: payload }); return draftId }
    const d = await api('/api/emails/drafts', { method: 'POST', body: payload })
    setDraftId(d.id)
    setStatus(d.status_label)
    return d.id
  }
  const mark = async (id, st, extra = {}) => {
    const d = await api(`/api/emails/drafts/${id}/status`, { method: 'POST', body: { status: st, ...extra } })
    setStatus(d.status_label)
  }
  const run = (fn) => async () => {
    setBusy(true)
    try { await fn() } catch (e) { toast(e.message, 'error') } finally { setBusy(false) }
  }

  const copy = run(async () => {
    await navigator.clipboard.writeText(`Objet : ${mail.subject}\n\n${mail.body}`)
    toast('Texte copié dans le presse-papiers')
  })

  const mailto = run(async () => {
    const id = await saveDraft()
    let body = mail.body
    if (body.length > 1800) {
      body = body.slice(0, 1800) + '\n[…]'
      toast("Texte long : la messagerie peut tronquer le corps. Utilisez « Copier » ou le fichier .eml pour le texte complet.", 'error')
    }
    const href = `mailto:${encodeURIComponent(mail.to_email || '')}?subject=${encodeURIComponent(mail.subject)}&body=${encodeURIComponent(body).replace(/%0A/g, '%0D%0A')}${mail.cc ? '&cc=' + encodeURIComponent(mail.cc) : ''}`
    window.location.href = href
    await mark(id, 'ouvert_messagerie')
    toast("Messagerie ouverte : l'email n'est PAS envoyé tant que vous ne l'envoyez pas vous-même.")
  })

  const eml = run(async () => {
    const id = await saveDraft()
    await download('/api/emails/eml', { method: 'POST', body: { to_email: mail.to_email, cc: mail.cc, subject: mail.subject, body: mail.body, attach_property_ids: attach ? mail.property_ids : [], draft_id: id }, filename: 'brouillon.eml' })
    setStatus('Fichier .eml téléchargé (non envoyé)')
  })

  const outlook = run(async () => {
    const id = await saveDraft()
    const base = (settings?.outlook_agent_url || 'http://127.0.0.1:8765').replace(/\/$/, '')
    const attachments = []
    if (attach) for (const pid of mail.property_ids || []) attachments.push(await api(`/api/emails/attachments/${pid}`))
    let res
    try {
      res = await fetch(`${base}/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Agent-Token': outlookToken() },
        body: JSON.stringify({ to: mail.to_email, cc: mail.cc, subject: mail.subject, body: mail.body, attachments }),
      })
    } catch {
      throw new Error("Agent Outlook injoignable sur ce poste. Lancez l'agent Windows ou utilisez le fichier .eml.")
    }
    const data = await res.json().catch(() => ({}))
    if (!res.ok || !data.ok) throw new Error(data.error || "L'agent Outlook a refusé la demande (jeton d'appairage ?).")
    await mark(id, 'brouillon_outlook')
    toast('Brouillon créé dans Outlook (non envoyé).')
  })

  const markSent = run(async () => {
    const id = draftId || (await saveDraft())
    await mark(id, 'envoye_confirme', { confirm_sent: true })
    toast('Envoi enregistré dans l\'historique.')
    onDone && onDone()
  })

  const save = run(async () => { await saveDraft(); toast('Brouillon enregistré') })

  return (
    <Modal title="Préparer un email" onClose={onClose} wide footer={mail && can('write') && (
      <>
        <button className="btn" onClick={copy} disabled={busy}><Icon name="copy" />Copier le texte</button>
        <button className="btn" onClick={mailto} disabled={busy}><Icon name="mail" />Ouvrir dans la messagerie</button>
        {settings?.outlook_enabled && <button className="btn" onClick={outlook} disabled={busy} title="Outlook classique Windows via l'agent local"><Icon name="briefcase" />Brouillon Outlook</button>}
        <button className="btn" onClick={eml} disabled={busy} title="Fichier .eml ouvrable dans Outlook (classique ou nouveau), Apple Mail, Thunderbird"><Icon name="download" />Fichier .eml</button>
        <button className="btn btn-primary" onClick={save} disabled={busy}>Enregistrer le brouillon</button>
      </>
    )}>
      {!mail ? <div className="spinner" /> : (
        <div className="stack">
          <div className="form-grid">
            <Field label="Modèle">
              <select value={template} onChange={(e) => setTemplate(e.target.value)}>
                {Object.entries(TEMPLATES).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
            </Field>
            <Field label="À"><input type="email" value={mail.to_email || ''} onChange={set('to_email')} placeholder="destinataire@…" /></Field>
            <Field label="Cc"><input type="text" value={mail.cc || ''} onChange={set('cc')} /></Field>
          </div>
          {mail.warnings?.map((w) => <div key={w} className="alert warn small">{w}</div>)}
          <Field label="Objet"><input type="text" value={mail.subject} onChange={set('subject')} /></Field>
          <Field label="Message (entièrement modifiable)"><textarea value={mail.body} onChange={set('body')} style={{ minHeight: 320, fontFamily: 'inherit' }} /></Field>
          {mail.property_ids?.length > 0 && (
            <label className="check"><input type="checkbox" checked={attach} onChange={(e) => setAttach(e.target.checked)} />Joindre les fiches PDF ({mail.property_ids.length}) — fichier .eml et brouillon Outlook uniquement (impossible via mailto)</label>
          )}
          <div className="alert info small">
            L'application n'envoie aucun email. Ouvrir la messagerie, créer un brouillon Outlook ou télécharger un .eml ne vaut pas envoi.
            {status && <div style={{ marginTop: 6 }}><b>Statut :</b> {status}</div>}
          </div>
          {draftId && (
            <div className="row">
              <label className="check"><input type="checkbox" checked={confirmSent} onChange={(e) => setConfirmSent(e.target.checked)} />Je confirme avoir envoyé ce message depuis ma messagerie</label>
              <button className="btn btn-accent btn-sm" disabled={!confirmSent || busy} onClick={markSent}><Icon name="check" />Marquer comme envoyé</button>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
