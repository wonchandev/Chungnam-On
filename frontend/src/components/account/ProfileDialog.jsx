import { useCallback, useState } from 'react'
import { apiRequest } from '../../api/client.js'
import useHomeSession from '../../pages/Home/hooks/useHomeSession.js'
import useHomeResource from '../../pages/Home/hooks/useHomeResource.js'
import HomeDialog from '../../pages/Home/components/HomeDialog.jsx'
import AuthInput from '../../pages/Auth/components/AuthInput.jsx'
import '../../pages/Auth/auth.css'

const fields = [
  ['name', '이름', 'text', 50], ['email', '이메일', 'email', 254],
  ['phone', '전화번호', 'tel', 20], ['nationality', '국적', 'text', 50], ['visa_type', '비자 종류', 'text', 20],
]

function ProfileForm({ user, options }) {
  const [values, setValues] = useState(() => Object.fromEntries(fields.map(([name]) => [name, user[name] || ''])))
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true); setErrors({}); setNotice('')
    try {
      await apiRequest('auth/me/', { ...options(), method: 'PATCH', body: values })
      setNotice('정보를 저장했습니다.')
      window.dispatchEvent(new Event('profile-updated'))
    } catch (error) {
      setErrors(error.detail && typeof error.detail === 'object' ? error.detail : {})
      setNotice(error.status === 401 ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : error.message)
    } finally { setBusy(false) }
  }
  return <div className="auth-page account-profile"><p>아이디: {user.username} · {user.role === 'employer' ? '사업주' : '근로자'}</p>
    <form onSubmit={submit}><fieldset disabled={busy}>
      {fields.map(([name, label, type, maxLength]) => <AuthInput key={name} name={name} label={label} type={type} maxLength={maxLength} value={values[name]} error={errors[name] ? [].concat(errors[name]).join(' ') : ''} onChange={event => { setValues(current => ({ ...current, [name]: event.target.value })); setNotice('') }} />)}
      {notice && <p role="status">{notice}</p>}
      <button className="auth-button" type="submit">{busy ? '저장 중…' : '변경사항 저장'}</button>
    </fieldset></form>
  </div>
}

export default function ProfileDialog({ onClose }) {
  const { session, saveSession } = useHomeSession()
  const options = useCallback(signal => ({ signal, accessToken: session?.access, refreshToken: session?.refresh, onRefresh: saveSession }), [session, saveSession])
  const load = useCallback(signal => apiRequest('auth/me/', options(signal)), [options])
  const profile = useHomeResource(load)
  return <HomeDialog title="내 정보 수정" onClose={onClose}>
    {profile.loading && <p role="status">정보를 불러오는 중…</p>}
    {profile.error && <div role="alert"><p>{profile.error.message}</p><button type="button" onClick={profile.retry}>다시 시도</button></div>}
    {profile.data && <ProfileForm user={profile.data} options={options} />}
  </HomeDialog>
}
