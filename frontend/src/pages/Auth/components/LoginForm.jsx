import { useRef, useState } from 'react'
import { apiRequest } from '../../../api/client.js'
import AuthInput from './AuthInput.jsx'

export default function LoginForm({ onSuccess, initialUsername = '' }) {
  const [values, setValues] = useState({ username: initialUsername, password: '' })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)

  function change(event) {
    setValues(current => ({ ...current, [event.target.name]: event.target.value }))
    setErrors({})
  }
  async function submit(event) {
    event.preventDefault()
    if (pending.current) return
    pending.current = true
    setBusy(true)
    setErrors({})
    try {
      const tokens = await apiRequest('auth/login/', { method: 'POST', body: values })
      onSuccess(tokens)
    } catch (error) {
      const fields = {}
      for (const name of ['username', 'password', 'non_field_errors']) {
        if (error.detail?.[name]) fields[name] = [].concat(error.detail[name]).join(' ')
      }
      setErrors({ ...fields, form: error.status === 401 ? '아이디 또는 비밀번호를 확인해 주세요.' : error.message })
    } finally {
      pending.current = false
      setBusy(false)
    }
  }
  return <form onSubmit={submit}>
    <fieldset disabled={busy}>
      <AuthInput label="아이디" name="username" value={values.username} onChange={change} error={errors.username} autoComplete="username" required />
      <AuthInput label="비밀번호" name="password" type="password" value={values.password} onChange={change} error={errors.password} autoComplete="current-password" required />
      {errors.form && <div className="auth-error" role="alert">{errors.form}{errors.non_field_errors && <p>{errors.non_field_errors}</p>}</div>}
      <button className="auth-button" type="submit">{busy ? '로그인 중…' : '로그인'}</button>
    </fieldset>
  </form>
}
