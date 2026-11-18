import { useCallback, useState } from 'react'
import { Users } from 'lucide-react'
import { homeApi } from '../api/home.js'
import useHomeResource from '../hooks/useHomeResource.js'
import { rows } from '../utils/formatters.js'

// 이 공고에 연결된 동행 모집 글 + 같이 갈 사람 모집하기 (공고 상세에서 사용)
export default function JobCompanions({ job, session, options, onLogin }) {
  const [version, setVersion] = useState(0)
  const [override, setOverride] = useState({})
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ title: '', capacity: 2, meet_place: '' })
  const load = useCallback((signal) => homeApi.companions(job.id, options(signal)), [job.id, options, version]) // eslint-disable-line react-hooks/exhaustive-deps
  const resource = useHomeResource(load)
  const list = rows(resource.data).map((post) => override[post.id] || post)

  async function toggle(post) {
    if (!session) { onLogin(); return }
    setBusy(true); setError('')
    try {
      const next = await homeApi.joinCompanion(post.id, post.is_joined, options())
      setOverride((value) => ({ ...value, [post.id]: next }))
    } catch (failure) { setError(failure.message) } finally { setBusy(false) }
  }

  async function create(event) {
    event.preventDefault()
    if (!session) { onLogin(); return }
    setBusy(true); setError('')
    try {
      await homeApi.createCompanion({ title: form.title.trim(), job: job.id, region: job.region?.code || null, capacity: Number(form.capacity), meet_place: form.meet_place.trim() }, options())
      setOpen(false); setForm({ title: '', capacity: 2, meet_place: '' }); setVersion((value) => value + 1)
    } catch (failure) { setError(failure.detail?.title?.[0] || failure.message) } finally { setBusy(false) }
  }

  return <section className="home-companions" aria-labelledby="companion-title">
    <div className="home-companions-head"><h3 id="companion-title"><Users size={18} aria-hidden="true" />이 공고 같이 갈 사람</h3><button type="button" onClick={() => session ? setOpen(!open) : onLogin()}>{open ? '닫기' : '동행 모집하기'}</button></div>
    {open && <form className="home-companion-form" onSubmit={create}>
      <label>제목<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} maxLength={150} required placeholder="예: 천안역에서 같이 출발해요" /></label>
      <label>모집 인원 (본인 제외)<input type="number" min="1" max="20" value={form.capacity} onChange={(event) => setForm({ ...form, capacity: event.target.value })} required /></label>
      <label>만날 장소 (선택)<input value={form.meet_place} onChange={(event) => setForm({ ...form, meet_place: event.target.value })} maxLength={150} /></label>
      <button className="home-primary" disabled={busy || !form.title.trim()}>{busy ? '등록 중…' : '등록하기'}</button>
    </form>}
    {resource.loading ? <p className="home-muted" role="status">불러오는 중…</p> : resource.error ? <p className="home-muted" role="alert">동행 모집 글을 불러오지 못했어요.</p> : !list.length ? <p className="home-muted">아직 동행 모집 글이 없어요. 먼저 올려 보세요.</p> : <ul className="home-companion-list">{list.map((post) => <li key={post.id}>
      <div><strong>{post.title}</strong><small>{post.author?.name} · {post.participant_count}/{post.capacity}명{post.meet_place ? ` · ${post.meet_place}` : ''}</small></div>
      {post.is_mine ? <span className="home-tag">내 글</span> : <button type="button" disabled={busy || (post.status !== 'open' && !post.is_joined)} onClick={() => toggle(post)}>{post.is_joined ? '참여 취소' : post.status === 'open' ? '참여하기' : '마감'}</button>}
    </li>)}</ul>}
    {error && <p className="home-notice" role="alert">{error}</p>}
  </section>
}
