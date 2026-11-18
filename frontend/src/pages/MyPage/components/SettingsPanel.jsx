import { useRef, useState } from 'react'
import { Bell, Languages, LockKeyhole, Save } from 'lucide-react'
import FormSelect from '../../../components/FormSelect.jsx'
import AuthInput from '../../Auth/components/AuthInput.jsx'
import { myRequest, errorText, fieldErrors, fieldError } from '../api.js'

function PasswordForm() {
  const [values, setValues] = useState({ old_password: '', new_password: '', confirmation: '' })
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState('')
  const pending = useRef(false)
  function change(event) { setValues(current => ({ ...current, [event.target.name]: event.target.value })); setErrors({}); setNotice('') }
  async function save(event) {
    event.preventDefault()
    if (pending.current) return
    if (values.new_password !== values.confirmation) { setErrors({ confirmation: '비밀번호가 일치하지 않습니다.' }); return }
    if (values.new_password.length < 8 || /^\d+$/.test(values.new_password)) { setErrors({ new_password: '8자 이상이며 숫자로만 구성되지 않은 비밀번호를 입력해 주세요.' }); return }
    pending.current = true; setBusy(true); setErrors({}); setNotice('')
    try {
      await myRequest('auth/password/', { method: 'PATCH', body: { old_password: values.old_password, new_password: values.new_password } })
      setValues({ old_password: '', new_password: '', confirmation: '' }); setNotice('비밀번호를 변경했어요.')
    } catch (error) { setErrors({ ...fieldErrors(error), form: errorText(error) }) }
    finally { pending.current = false; setBusy(false) }
  }
  return <section className="my-card"><div className="my-section-heading"><h2><LockKeyhole size={20} />비밀번호 변경</h2></div><form className="my-form" onSubmit={save}><fieldset disabled={busy}>
    <AuthInput name="old_password" label="현재 비밀번호" type="password" autoComplete="current-password" required value={values.old_password} onChange={change} error={fieldError(errors, 'old_password')} />
    <AuthInput name="new_password" label="새 비밀번호" type="password" autoComplete="new-password" required value={values.new_password} onChange={change} error={fieldError(errors, 'new_password')} />
    <AuthInput name="confirmation" label="새 비밀번호 확인" type="password" autoComplete="new-password" required value={values.confirmation} onChange={change} error={fieldError(errors, 'confirmation')} />
    <p className="my-help">8자 이상 입력해 주세요. 흔한 비밀번호는 서버에서 추가 검증합니다.</p>
    {errors.form && <p className="my-error" role="alert">{errors.form}</p>}{notice && <p className="my-success" role="status">{notice}</p>}<button className="my-primary">{busy ? '변경 중…' : '비밀번호 변경'}</button>
  </fieldset></form></section>
}
export default function SettingsPanel({ user, languages, onSaved }) {
  const [language, setLanguage] = useState(user.preferred_language)
  const [notifications, setNotifications] = useState(user.notifications_enabled)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const pending = useRef(false)
  async function save(event) {
    event.preventDefault()
    if (pending.current) return
    pending.current = true; setBusy(true); setError(''); setNotice('')
    try { onSaved(await myRequest('auth/me/', { method: 'PATCH', body: { preferred_language: language, notifications_enabled: notifications } })); setNotice('설정을 저장했어요.') }
    catch (failure) { setError(errorText(failure)) }
    finally { pending.current = false; setBusy(false) }
  }
  return <><section className="my-card"><div className="my-section-heading"><h2>앱 설정</h2><span>나에게 편한 이용 환경</span></div><form className="my-form" onSubmit={save}><fieldset disabled={busy}>
    <div className="my-setting-heading"><Languages size={19} /><div><strong>선호 언어</strong><p>번역과 새 대화에 사용할 선호 언어를 저장해요.</p></div></div><FormSelect name="preferred_language" label="사용 언어" value={language} options={languages.map(item => ({ value: item.code, label: item.native_name }))} onChange={event => { setLanguage(event.target.value); setNotice('') }} />
    <label className="my-toggle-row"><Bell size={21} /><span><strong>알림 수신</strong><small>지원 결과, 새 대화 등 서비스 알림을 받아요.</small></span><input type="checkbox" role="switch" checked={notifications} onChange={event => { setNotifications(event.target.checked); setNotice('') }} /><span className="my-toggle-track" aria-hidden="true" /></label>
    {error && <p className="my-error" role="alert">{error}</p>}{notice && <p className="my-success" role="status">{notice}</p>}<button className="my-primary"><Save size={17} />{busy ? '저장 중…' : '설정 저장'}</button>
  </fieldset></form></section><PasswordForm /></>
}
