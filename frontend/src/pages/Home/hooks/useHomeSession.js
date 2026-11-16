import { useCallback, useState } from 'react'
import { apiRequest } from '../../../api/client.js'

const STORAGE_KEY = 'chungnam-home-session'

function readSession() {
  try { return JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null') } catch { return null }
}

export default function useHomeSession() {
  const [session, setSession] = useState(readSession)
  const [notice, setNotice] = useState('')
  const saveSession = useCallback((tokens) => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tokens))
    setSession(tokens)
  }, [])

  function login(tokens) {
    saveSession(tokens)
    setNotice('로그인했어요.')
  }

  async function logout() {
    try { await apiRequest('auth/logout/', { method: 'POST', accessToken: session.access, body: { refresh: session.refresh } }) }
    catch { /* Expired sessions must still be removable locally. */ }
    sessionStorage.removeItem(STORAGE_KEY)
    setSession(null)
    setNotice('로그아웃했어요.')
  }

  return { session, saveSession, notice, login, logout }
}
