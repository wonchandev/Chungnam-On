import { useRef, useState } from 'react'
import { Camera, Check, Save } from 'lucide-react'
import AuthInput from '../../Auth/components/AuthInput.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import { myRequest, errorText, fieldErrors, fieldError } from '../api.js'
import '../../Auth/auth.css'

const fields = [['name', '이름', 'text', 50], ['email', '이메일', 'email', 254], ['phone', '전화번호', 'tel', 20], ['nationality', '국적', 'text', 50], ['visa_type', '비자 종류', 'text', 20]]
export default function ProfileForm({ user, regions, onSaved }) {
  const [values, setValues] = useState(() => ({ ...Object.fromEntries(fields.map(([name]) => [name, user[name] || ''])), region: user.region || '' }))
  const [image, setImage] = useState(null)
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  const fileInput = useRef(null)
  function change(event) { setValues(current => ({ ...current, [event.target.name]: event.target.value })); setErrors({}); setNotice('') }
  async function save(event) {
    event.preventDefault()
    if (pending.current) return
    if (image && image.size > 5 * 1024 * 1024) { setErrors({ profile_image: '프로필 사진은 5MB 이하로 선택해 주세요.' }); return }
    pending.current = true; setBusy(true); setErrors({}); setNotice('')
    try {
      let body = { ...values, region: values.region || null }
      if (image) { body = new FormData(); for (const [key, value] of Object.entries(values)) body.set(key, value); body.set('profile_image', image) }
      const result = await myRequest('auth/me/', { method: 'PATCH', body })
      onSaved(result); setImage(null); if (fileInput.current) fileInput.current.value = ''
      setNotice('내 정보를 저장했어요.')
      window.dispatchEvent(new Event('profile-updated'))
    } catch (error) { setErrors({ ...fieldErrors(error), form: errorText(error) }) }
    finally { pending.current = false; setBusy(false) }
  }
  return <section className="my-card"><div className="my-section-heading"><h2>내 정보 수정</h2><span>나의 기본 프로필</span></div><form className="my-form" onSubmit={save}><fieldset disabled={busy}>
    <div className="my-readonly"><span>아이디</span><strong>{user.username}</strong><small>아이디와 회원 유형은 변경할 수 없어요.</small></div>
    <label className="my-file-field"><span><Camera size={17} />프로필 사진</span><input ref={fileInput} type="file" accept="image/*" onChange={event => { setImage(event.target.files?.[0] || null); setErrors({}); setNotice('') }} /><small>5MB 이하의 이미지</small></label>
    {errors.profile_image && <p className="my-error">{fieldError(errors, 'profile_image')}</p>}
    <div className="my-form-grid">{fields.map(([name, label, type, maxLength]) => <AuthInput key={name} name={name} label={label} type={type} maxLength={maxLength} value={values[name]} onChange={change} error={fieldError(errors, name)} autoComplete={name === 'name' ? 'name' : name === 'email' ? 'email' : name === 'phone' ? 'tel' : 'off'} />)}</div>
    <FormSelect name="region" label="거주지역" value={values.region} onChange={change} error={fieldError(errors, 'region')} options={[{ value: '', label: '선택 안 함' }, ...regions.map(region => ({ value: region.code, label: region.name }))]} />
    <p className="my-help">이메일·전화번호 인증 상태는 직접 변경할 수 없어요.</p><div className="my-verified"><span className={user.email_verified ? 'is-verified' : ''}><Check size={13} />이메일 {user.email_verified ? '인증됨' : '미인증'}</span><span className={user.phone_verified ? 'is-verified' : ''}><Check size={13} />전화번호 {user.phone_verified ? '인증됨' : '미인증'}</span></div>
    {errors.form && <p className="my-error" role="alert">{errors.form}</p>}{notice && <p className="my-success" role="status">{notice}</p>}
    <button className="my-primary" type="submit"><Save size={17} />{busy ? '저장 중…' : '내 정보 저장'}</button>
  </fieldset></form></section>
}
