import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, setUnauthorizedHandler, tokenStore } from '../services/api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

/**
 * status: 'loading' (checking saved token) | 'authed' | 'anon' | 'error' (server unreachable)
 * A saved token is only discarded when the server says it is invalid (401) - not when the
 * free-tier backend is simply asleep or offline.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(tokenStore.get() ? 'loading' : 'anon')
  const [notice, setNotice] = useState('')

  const check = useCallback(() => {
    if (!tokenStore.get()) { setStatus('anon'); return }
    setStatus('loading')
    api.me()
      .then((u) => { setUser(u); setStatus('authed') })
      .catch((e) => {
        if (e.status === 401) { tokenStore.clear(); setUser(null); setStatus('anon') }
        else setStatus('error')
      })
  }, [])

  useEffect(() => { check() }, [check])

  const logout = useCallback((message = '') => {
    tokenStore.clear(); setUser(null); setStatus('anon'); setNotice(message)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => logout('Your session expired. Please sign in again.'))
    return () => setUnauthorizedHandler(null)
  }, [logout])

  const startSession = (res) => { tokenStore.set(res.token); setUser(res.user); setStatus('authed'); setNotice('') }

  const value = useMemo(() => ({
    user, status, notice, retry: check, logout, setUser,
    login: async (email, password) => startSession(await api.login({ email, password })),
    register: async (payload) => startSession(await api.register(payload)),
  }), [user, status, notice, check, logout])

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}
