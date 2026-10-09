import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, setCsrf } from './api.js'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined) // undefined = vérification en cours
  const [settings, setSettings] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const me = await api('/api/auth/me')
      setCsrf(me.csrf_token)
      setUser(me.user)
      setSettings(await api('/api/settings'))
    } catch {
      setCsrf(null)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    refresh()
    const onUnauth = () => { setCsrf(null); setUser(null) }
    window.addEventListener('immopro:unauthorized', onUnauth)
    return () => window.removeEventListener('immopro:unauthorized', onUnauth)
  }, [refresh])

  const login = async (username, password) => {
    await api('/api/auth/login', { method: 'POST', body: { username, password } })
    await refresh()
  }
  const logout = async () => {
    try { await api('/api/auth/logout', { method: 'POST' }) } finally { setCsrf(null); setUser(null) }
  }
  const can = (what) => (what === 'write' ? ['admin', 'collaborateur'].includes(user?.role) : what === 'admin' ? user?.role === 'admin' : !!user)

  return <AuthCtx.Provider value={{ user, settings, setSettings, login, logout, refresh, can }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
