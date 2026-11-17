import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import LoginPage from './LoginPage.jsx'
import AuthBrand from './components/AuthBrand.jsx'
import AuthInput from './components/AuthInput.jsx'
import { apiRequest } from '../../api/client.js'
import { saveSession } from '../../api/session.js'
import FormSelect from '../../components/FormSelect.jsx'
import './auth.css'

const initial = { username: '', password: '', confirmation: '', role: 'worker', name: '', email: '', phone: '', nationality: '', preferred_language: 'ko', visa_type: '', region: '', company_name: '', business_number: '', representative: '', address: '', is_agency: false }
const fieldLabels = { username: '아이디', password: '비밀번호', confirmation: '비밀번호 확인', role: '회원 유형', name: '이름', email: '이메일', phone: '전화번호', nationality: '국적', preferred_language: '사용 언어', visa_type: '비자 종류', region: '거주지역', company_name: '회사명', business_number: '사업자등록번호', representative: '대표자', address: '사업장 주소', company: '사업장 정보', non_field_errors: '가입 정보' }

export default function AuthPage({ mode }) {
  // Remount the form when switching between login and signup.
  return mode === 'signup' ? <AuthForm signup /> : <LoginPage />
}

function AuthForm({ signup }) {
  const navigate = useNavigate()
  const [values, setValues] = useState(initial)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const [options, setOptions] = useState({ regions: [], languages: [] })
  const [optionsError, setOptionsError] = useState('')
  useEffect(() => {
    document.title = `${signup ? '회원가입' : '로그인'} | 충남온`
    return () => { document.title = '충남온 | 일자리와 생활을 연결하다' }
  }, [signup])
  useEffect(() => {
    if (!signup) return
    const controller = new AbortController()
    Promise.all([apiRequest('regions/', { signal: controller.signal }), apiRequest('languages/', { signal: controller.signal })])
      .then(([regions, languages]) => setOptions({ regions: regions.results || regions, languages }))
      .catch(error => { if (error.name !== 'AbortError') setOptionsError('지역·언어 목록을 가져오지 못했습니다. 새로고침해 주세요.') })
    return () => controller.abort()
  }, [signup])

  function change(event) {
    const { name, value, type, checked } = event.target
    setValues(current => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
    setErrors({})
  }
  const passwordIssues = []
  if (values.password.length < 8) passwordIssues.push('8자 이상 입력해 주세요.')
  if (/^\d+$/.test(values.password)) passwordIssues.push('숫자로만 구성된 비밀번호는 사용할 수 없습니다.')
  if (values.confirmation && values.password !== values.confirmation) passwordIssues.push('비밀번호 확인이 일치하지 않습니다.')

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    if (signup && (passwordIssues.length || values.password !== values.confirmation)) {
      setErrors({ password: passwordIssues.join(' '), confirmation: values.password !== values.confirmation ? '비밀번호가 일치하지 않습니다.' : '' })
      return
    }
    setBusy(true)
    setErrors({})
    try {
      if (signup) {
        const { username, password, role, name, email, phone, nationality, preferred_language, visa_type, region } = values
        const body = { username, password, role, name, email, phone, nationality, preferred_language, visa_type, region: region || null }
        if (role === 'employer') body.company = { name: values.company_name, business_number: values.business_number, representative: values.representative, address: values.address, is_agency: values.is_agency }
        await apiRequest('auth/register/', { method: 'POST', body })
        setValues({ ...initial, username })
        try {
          const tokens = await apiRequest('auth/login/', { method: 'POST', body: { username, password } })
          saveSession(tokens)
          navigate('/', { replace: true })
        } catch {
          navigate('/login', { replace: true, state: { signupComplete: true, username } })
        }

      }
    } catch (error) {
      const detail = error.detail
      const fields = {}
      if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
        for (const [key, value] of Object.entries(detail)) {
          if (key === 'company' && value && typeof value === 'object' && !Array.isArray(value)) {
            for (const [field, messages] of Object.entries(value)) fields[field === 'name' ? 'company_name' : field] = [].concat(messages).join(' ')
          } else fields[key] = [].concat(value).join(' ')
        }
      }
      setErrors({ ...fields, form: !signup && error.status === 401 ? '아이디 또는 비밀번호를 확인해 주세요.' : error.message })
    } finally { setBusy(false) }
  }

  function field(name, label, type = 'text', required = false, props = {}) {
    if (type === 'password') return <AuthInput key={name} label={label} name={name} type={type} value={values[name]} onChange={change} required={required} error={errors[name]} {...props} />
    return <label className="auth-field" key={name}>{label}<input name={name} type={type} value={values[name]} onChange={change} required={required} aria-invalid={!!errors[name]} aria-describedby={errors[name] ? `${name}-error` : undefined} {...props} />{errors[name] && <span className="auth-error" id={`${name}-error`}>{errors[name]}</span>}</label>
  }

  return <section className="auth-page">
    <AuthBrand />
    <h1>{signup ? '회원가입' : '로그인'}</h1>
    <p>{signup ? '근로자 또는 사업주 계정을 만들어 주세요.' : '아이디로 로그인해 주세요.'}</p>
    <form onSubmit={submit}>
      <fieldset disabled={busy}>
        {field('username', '아이디', 'text', true, { autoComplete: 'username', maxLength: 150, pattern: '[\\p{L}\\p{N}@.+_\\-]+', title: '문자, 숫자 및 @ . + - _만 사용할 수 있습니다.' })}
        {field('password', '비밀번호', 'password', true, { autoComplete: signup ? 'new-password' : 'current-password' })}
        {signup && <>
          <p className="auth-help">8자 이상, 숫자로만 구성되지 않은 비밀번호를 사용하세요.</p>
          {field('confirmation', '비밀번호 확인', 'password', true, { autoComplete: 'new-password' })}
          {values.password && <p className={passwordIssues.length ? 'auth-error' : 'auth-help'} role="status">{passwordIssues.join(' ') || '비밀번호 기본 조건을 충족했습니다.'}</p>}
          <FormSelect label="회원 유형" name="role" value={values.role} onChange={change} error={errors.role} options={[{ value: 'worker', label: '근로자' }, { value: 'employer', label: '사업주 / 인력사무소' }]} />
          {field('name', '이름', 'text', false, { maxLength: 50, autoComplete: 'name' })}
          {field('email', '이메일', 'email', false, { autoComplete: 'email' })}
          {field('phone', '전화번호', 'tel', false, { maxLength: 20, autoComplete: 'tel' })}
          {field('nationality', '국적', 'text', false, { maxLength: 50 })}
          <FormSelect label="사용 언어" name="preferred_language" value={values.preferred_language} onChange={change} error={errors.preferred_language} options={options.languages.length ? options.languages.map(language => ({ value: language.code, label: language.native_name })) : [{ value: 'ko', label: '한국어' }]} />
          <FormSelect label="거주지역" name="region" value={values.region} onChange={change} error={errors.region} options={[{ value: '', label: '선택 안 함' }, ...options.regions.map(region => ({ value: region.code, label: region.name }))]} />
          {field('visa_type', '비자 종류 (예: E-9, H-2)', 'text', false, { maxLength: 20 })}
          <p className="auth-help">선택 항목입니다. 체류자격 코드를 입력하거나 비워두세요.</p>
          {optionsError && <p role="alert" className="auth-error">{optionsError}</p>}
          {values.role === 'employer' && <div className="auth-company"><h2>사업장 정보</h2>
            {field('company_name', '회사명', 'text', true, { maxLength: 100 })}
            {field('business_number', '사업자등록번호', 'text', true, { pattern: '[0-9]{3}-?[0-9]{2}-?[0-9]{5}', title: '숫자 10자리 또는 000-00-00000 형식으로 입력해 주세요.' })}
            {field('representative', '대표자', 'text', true, { maxLength: 50 })}
            {field('address', '사업장 주소', 'text', true, { maxLength: 200 })}
            <label><input type="checkbox" name="is_agency" checked={values.is_agency} onChange={change} /> 인력사무소입니다</label>
          </div>}
        </>}
        {errors.form && <div className="auth-error-summary" role="alert">
          <strong>회원가입을 완료하지 못했습니다</strong>
          {Object.entries(errors).some(([key]) => key !== 'form') ? <ul>{Object.entries(errors).filter(([key, message]) => key !== 'form' && message).map(([key, message]) => <li key={key}><strong>{fieldLabels[key] || key}:</strong> {message}</li>)}</ul> : <p>{errors.form}</p>}
          <span>해당 입력란을 수정한 뒤 다시 시도해 주세요.</span>
        </div>}
        <button className="auth-button" type="submit">{busy ? '처리 중…' : signup ? '회원가입' : '로그인'}</button>
      </fieldset>
    </form>
    <Link to={signup ? '/login' : '/signup'}>{signup ? '이미 계정이 있나요? 로그인' : '계정이 없나요? 회원가입'}</Link>
  </section>
}
