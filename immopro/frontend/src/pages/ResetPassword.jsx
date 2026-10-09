import { useState } from 'react'
import { api } from '../api.js'

export default function ResetPassword() {
  const token = new URLSearchParams(window.location.search).get('token') || ''
  const [p1, setP1] = useState('')
  const [p2, setP2] = useState('')
  const [msg, setMsg] = useState(null)
  const submit = async (e) => {
    e.preventDefault()
    if (p1 !== p2) return setMsg({ type: 'danger', text: 'Les mots de passe ne correspondent pas.' })
    try {
      await api('/api/auth/reset', { method: 'POST', body: { token, new_password: p1 } })
      setMsg({ type: 'ok', text: 'Mot de passe modifié. Vous pouvez vous connecter.' })
      window.history.replaceState(null, '', '/reinitialisation')
    } catch (err) { setMsg({ type: 'danger', text: err.message }) }
  }
  return (
    <div className="login-form" style={{ minHeight: '100%' }}>
      <form onSubmit={submit}>
        <h2>Nouveau mot de passe</h2>
        {msg && <div className={`alert ${msg.type}`}>{msg.text}</div>}
        {msg?.type === 'ok' ? <a className="btn btn-primary" href="/">Se connecter</a> : (<>
          <label className="field">Nouveau mot de passe<input type="password" autoComplete="new-password" value={p1} onChange={(e) => setP1(e.target.value)} required minLength={12} /></label>
          <label className="field">Confirmation<input type="password" autoComplete="new-password" value={p2} onChange={(e) => setP2(e.target.value)} required /></label>
          <p className="small muted">12 caractères minimum, avec au moins 3 types de caractères (minuscules, majuscules, chiffres, symboles).</p>
          <button className="btn btn-primary">Valider</button>
        </>)}
      </form>
    </div>
  )
}
