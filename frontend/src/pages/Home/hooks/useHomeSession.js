import { useState, useSyncExternalStore } from 'react'
import { apiRequest } from '../../../api/client.js'
import { getSession, subscribeSession, saveSession } from '../../../api/session.js'

export default function useHomeSession() {
  const session = useSyncExternalStore(subscribeSession, getSession)
  const [notice, setNotice] = useState('')

  function login(tokens) {
    saveSession(tokens)
    setNotice('로그인했어요.')
  }

  async function logout() {
    if (!window.confirm('로그아웃하시겠습니까?')) return false
    try { await apiRequest('auth/logout/', { method: 'POST', accessToken: session.access, body: { refresh: session.refresh } }) }
    catch { /* Expired sessions must still be removable locally. */ }
    saveSession(null)
    setNotice('로그아웃했어요.')
    return true
  }

  return { session, saveSession, notice, login, logout }
}
