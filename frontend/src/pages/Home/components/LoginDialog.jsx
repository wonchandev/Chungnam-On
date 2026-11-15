import { useState } from 'react'
import { apiRequest } from '../../../api/client.js'
import HomeDialog from './HomeDialog.jsx'

export default function LoginDialog({ onClose, onLogin }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    const data = new FormData(event.currentTarget)
    try {
      const tokens = await apiRequest('auth/login/', { method: 'POST', body: { username: data.get('username'), password: data.get('password') } })
      onLogin(tokens)
    } catch (error) { setError(error.status === 401 ? '아이디와 비밀번호를 확인해 주세요.' : error.message) }
    finally { setBusy(false) }
  }
  return <HomeDialog title="로그인" onClose={onClose}><p>관심 공고를 저장하려면 로그인해 주세요.</p><form className="home-login-form" onSubmit={submit}>
    <label>아이디<input name="username" autoComplete="username" required /></label>
    <label>비밀번호<input name="password" type="password" autoComplete="current-password" required /></label>
    {error && <p role="alert">{error}</p>}
    <button className="home-primary" disabled={busy}>{busy ? '로그인 중…' : '로그인'}</button>
  </form></HomeDialog>
}
