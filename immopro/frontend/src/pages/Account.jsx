import { useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Field, useToast } from '../components/ui.jsx'

export default function Account() {
  const { user, refresh } = useAuth()
  const toast = useToast()
  const [profile, setProfile] = useState({ full_name: user.full_name || '', email: user.email || '', phone: user.phone || '', email_signature: user.email_signature || '' })
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const saveProfile = async (e) => {
    e.preventDefault()
    try { await api('/api/auth/me', { method: 'PUT', body: { ...profile, email: profile.email || null } }); await refresh(); toast('Profil enregistré') } catch (err) { toast(err.message, 'error') }
  }
  const changePw = async (e) => {
    e.preventDefault()
    if (pw.new_password !== pw.confirm) return toast('Les mots de passe ne correspondent pas.', 'error')
    try { await api('/api/auth/change-password', { method: 'POST', body: pw }); setPw({ current_password: '', new_password: '', confirm: '' }); await refresh(); toast('Mot de passe modifié. Vos autres sessions ont été fermées.') } catch (err) { toast(err.message, 'error') }
  }
  return (
    <>
      <div className="page-head"><div><h1>Mon compte</h1><p>{user.username} · {user.role}</p></div></div>
      <div className="grid g2">
        <form className="card card-body stack" onSubmit={saveProfile}>
          <h2>Profil et signature</h2>
          <p className="small muted" style={{ margin: 0 }}>Ces coordonnées apparaissent dans les emails et fiches PDF que vous générez.</p>
          <Field label="Nom complet"><input type="text" value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} /></Field>
          <Field label="Email professionnel"><input type="email" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></Field>
          <Field label="Téléphone"><input type="tel" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} /></Field>
          <Field label="Signature email" hint="Laissez vide pour une signature automatique (nom, société, téléphone, email)."><textarea value={profile.email_signature} onChange={(e) => setProfile({ ...profile, email_signature: e.target.value })} /></Field>
          <div><button className="btn btn-primary">Enregistrer</button></div>
        </form>
        <form className="card card-body stack" onSubmit={changePw}>
          <h2>Changer de mot de passe</h2>
          {user.must_change_password && <div className="alert warn">Vous utilisez un mot de passe temporaire : choisissez-en un nouveau.</div>}
          <Field label="Mot de passe actuel"><input type="password" autoComplete="current-password" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} required /></Field>
          <Field label="Nouveau mot de passe" hint="12 caractères minimum, 3 types de caractères."><input type="password" autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} required /></Field>
          <Field label="Confirmation"><input type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required /></Field>
          <div><button className="btn btn-primary">Modifier</button></div>
        </form>
      </div>
    </>
  )
}
