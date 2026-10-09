import { useState } from 'react'
import { useAuth } from '../auth.jsx'

export default function Login() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try { await login(username, password) } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return (
    <div className="login-wrap">
      <section className="login-hero">
        <div className="brand" style={{ padding: 0 }}><img src="/icons/icon.svg" alt="" width="40" />ImmoPro<small style={{ marginLeft: 6 }}>Entreprise</small></div>
        <div>
          <h1>Immobilier d'entreprise, du mandat à la visite.</h1>
          <p>Offres, demandes clients, matching explicable, recherche multisource et suivi commercial dans un espace privé et sécurisé.</p>
        </div>
        <p className="small" style={{ color: '#7f93b3' }}>Accès réservé aux utilisateurs autorisés. Connexions journalisées.</p>
        <svg className="skyline" viewBox="0 0 520 200" aria-hidden="true"><path fill="#fff" d="M0 200V120h60V80h40v40h30V60h70v60h40V100h60v100h30V70h80v130h40V110h70v90z" /></svg>
      </section>
      <section className="login-form">
        <form onSubmit={submit}>
          <h2 style={{ fontSize: 22 }}>Connexion</h2>
          <p className="muted" style={{ margin: 0 }}>Identifiez-vous pour accéder à votre espace.</p>
          {error && <div className="alert danger" role="alert">{error}</div>}
          <label className="field">Identifiant<input type="text" autoComplete="username" autoCapitalize="none" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus /></label>
          <label className="field">Mot de passe<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          <button className="btn btn-primary" style={{ minHeight: 46 }} disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</button>
          <p className="small muted">Mot de passe oublié ? Demandez un lien de réinitialisation à votre administrateur (lien à usage unique, valable 30 minutes).</p>
        </form>
      </section>
    </div>
  )
}
