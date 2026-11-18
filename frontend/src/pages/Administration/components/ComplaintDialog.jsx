import { useCallback, useRef, useState } from 'react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import useAdminResource from '../useAdminResource.js'
import AuthInput from '../../Auth/components/AuthInput.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import { adminRequest, complaintCategories, errorText } from '../api.js'
import ResourceState from './ResourceState.jsx'
import '../../Auth/auth.css'

function ComplaintDetail({ id }) {
  const load = useCallback(signal => adminRequest(`admin-info/complaints/${id}/`, { signal }), [id])
  const resource = useAdminResource(load)
  return <ResourceState resource={resource}>{complaint => <article className="admin-complaint-detail"><span className={`admin-status is-${complaint.status}`}>{complaint.status_label}</span><h3>{complaint.title}</h3><p className="admin-guide-updated">{complaint.category_label} · {new Date(complaint.created_at).toLocaleDateString('ko-KR')}</p><p className="admin-guide-body">{complaint.body}</p><div className="admin-answer"><h4>운영자 답변</h4><p className="admin-guide-body">{complaint.answer || '아직 등록된 답변이 없습니다. 답변이 등록되면 알림으로 안내해 드려요.'}</p>{complaint.answered_at && <time>{new Date(complaint.answered_at).toLocaleString('ko-KR')}</time>}</div></article>}</ResourceState>
}

function ComplaintForm({ onSaved }) {
  const [values, setValues] = useState({ category: 'visa', title: '', body: '' })
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const pending = useRef(false)
  function change(event) { setValues(current => ({ ...current, [event.target.name]: event.target.value })); setErrors({}) }
  async function submit(event) {
    event.preventDefault()
    if (pending.current) return
    if (!values.title.trim() || !values.body.trim()) { setErrors({ form: '제목과 내용을 입력해 주세요. 공백만으로 접수할 수 없습니다.' }); return }
    pending.current = true; setBusy(true); setErrors({})
    try {
      const result = await adminRequest('admin-info/complaints/', { method: 'POST', body: { ...values, title: values.title.trim(), body: values.body.trim() } })
      onSaved(result.id)
    } catch (error) {
      const detail = error.detail && typeof error.detail === 'object' && !Array.isArray(error.detail) ? error.detail : {}
      setErrors({ ...detail, form: errorText(error) })
    } finally { pending.current = false; setBusy(false) }
  }
  return <form className="admin-complaint-form" onSubmit={submit}>
    <p className="admin-info-note">충남온 운영자에게 전달되는 문의입니다. 정부기관의 공식 민원 접수나 행정 신청은 아닙니다.</p>
    <fieldset disabled={busy}>
      <FormSelect name="category" label="문의 분야" value={values.category} onChange={change} options={complaintCategories} error={errors.category ? [].concat(errors.category).join(' ') : ''} />
      <AuthInput name="title" label="제목" value={values.title} onChange={change} required maxLength={200} error={errors.title ? [].concat(errors.title).join(' ') : ''} />
      <label className="admin-input-label">문의 내용<textarea name="body" value={values.body} onChange={change} required rows={7} placeholder="도움이 필요한 내용을 자세히 작성해 주세요." aria-invalid={!!errors.body} aria-describedby="complaint-body-help" /></label>
      <p id="complaint-body-help" className="admin-footnote">여권번호·외국인등록번호 등 민감한 개인정보는 입력하지 마세요.</p>
      {errors.body && <p className="admin-error">{[].concat(errors.body).join(' ')}</p>}
      {errors.form && <p className="admin-error" role="alert">{errors.form}</p>}
      <button className="admin-primary" type="submit">{busy ? '접수 중…' : '문의 접수하기'}</button>
    </fieldset>
  </form>
}
export default function ComplaintDialog({ id, onClose, onSaved }) {
  return <HomeDialog title={id ? '내 문의 상세' : '민원·문의 접수'} onClose={onClose} className="admin-dialog"><div className="admin-dialog-content">{id ? <ComplaintDetail id={id} /> : <ComplaintForm onSaved={onSaved} />}</div></HomeDialog>
}
