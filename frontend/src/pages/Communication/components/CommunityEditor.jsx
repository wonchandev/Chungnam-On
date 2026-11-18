import { useState } from 'react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import { communicationRequest, errorMessage } from '../api.js'
import { categories } from './communityHelpers.js'

export default function CommunityEditor({ kind, initial, regions, onClose, onSaved }) {
  const companion = kind === 'companions'
  const editing = !!initial.id
  const [form, setForm] = useState({ title: initial.original_title || '', body: initial.original_body || '', category: initial.category || 'free', region: initial.region || '', capacity: 2, meet_place: '', meet_at: '' })
  const [image, setImage] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  function change(event) { setForm(value => ({ ...value, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setError('')
    if (!form.title.trim() || (!companion && !form.body.trim())) { setError('제목과 내용을 입력해 주세요.'); return }
    setBusy(true)
    try {
      let body
      if (companion) body = { title: form.title.trim(), body: form.body.trim(), region: form.region || null, capacity: Number(form.capacity), meet_place: form.meet_place.trim(), meet_at: form.meet_at ? new Date(form.meet_at).toISOString() : null }
      else {
        body = new FormData()
        for (const name of ['title', 'body', 'category', 'region']) body.append(name, form[name].trim())
        if (image) body.append('image', image)
      }
      const post = await communicationRequest(`community/${kind}/${editing ? `${initial.id}/` : ''}`, { method: editing ? 'PATCH' : 'POST', body })
      onSaved(post)
    } catch (error) { setError(errorMessage(error)); setBusy(false) }
  }
  return <HomeDialog title={editing ? '게시글 수정' : companion ? '동행 모집하기' : '새 이야기 쓰기'} onClose={() => { if (!busy) onClose() }} className="comm-community-dialog">
    <form className="comm-dialog-content" onSubmit={submit}><fieldset disabled={busy} className="comm-community-fields">
      <label className="comm-input-label">제목<input name="title" value={form.title} onChange={change} required maxLength={companion ? 150 : 200} placeholder={companion ? '어떤 동료를 찾고 있나요?' : '이야기의 제목을 입력해 주세요'} /></label>
      <div className="comm-community-filters"><FormSelect label="지역" name="region" value={form.region} onChange={change} options={regions} disabled={busy} />{!companion && <FormSelect label="분류" name="category" value={form.category} onChange={change} options={categories} disabled={busy} />}</div>
      <label className="comm-input-label">내용{companion && ' (선택)'}<textarea name="body" value={form.body} onChange={change} required={!companion} rows={6} placeholder="서로에게 도움이 되는 이야기를 나눠주세요." /></label>
      {companion ? <><label className="comm-input-label">만날 장소 (선택)<input name="meet_place" value={form.meet_place} onChange={change} maxLength={150} /></label><label className="comm-input-label">만날 일시 (선택)<input type="datetime-local" name="meet_at" value={form.meet_at} onChange={change} /></label><label className="comm-input-label">모집 인원<input type="number" min="1" max="32767" required name="capacity" value={form.capacity} onChange={change} /><span>작성자를 제외한 인원이에요.</span></label></> : <label className="comm-input-label">사진 (선택)<input type="file" accept="image/*" onChange={event => setImage(event.target.files?.[0] || null)} />{editing && initial.image && <span>새 사진을 선택하면 기존 사진이 변경돼요.</span>}</label>}
      <p className="comm-community-note">연락처나 외국인등록번호 등 개인정보를 공개하지 마세요.</p>
      {error && <p className="comm-error" role="alert">{error}</p>}
      <button className="comm-primary" disabled={busy}>{busy ? '저장 중…' : editing ? '수정하기' : '등록하기'}</button>
    </fieldset></form>
  </HomeDialog>
}
