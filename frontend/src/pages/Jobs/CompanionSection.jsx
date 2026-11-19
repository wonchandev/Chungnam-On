import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSession } from '../../api/session.js'
import { communicationRequest, errorMessage, items } from '../Communication/api.js'

const meetLabel = (value) =>
  !value ? '' : new Date(value).toLocaleString('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

export default function CompanionSection({ jobId }) {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', list: [] })
  const [busyId, setBusyId] = useState(null)
  const [notice, setNotice] = useState('')
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ title: '', capacity: 2, meet_place: '', meet_at: '' })

  const load = useCallback(
    (signal) =>
      communicationRequest('community/companions/', { signal, query: { status: 'open', job: jobId } })
        .then((data) =>
          setState({ loading: false, error: '', list: items(data) }),
        )
        .catch((e) => {
          if (e.name !== 'AbortError') {
            setState({ loading: false, error: errorMessage(e), list: [] })
          }
        }),
    [jobId],
  )

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  const toggleJoin = async (companion) => {
    if (!getSession()) {
      navigate('/login')
      return
    }
    setBusyId(companion.id)
    setNotice('')
    try {
      await communicationRequest(`community/companions/${companion.id}/join/`, {
        method: companion.is_joined ? 'DELETE' : 'POST',
        body: companion.is_joined ? undefined : {},
      })
      await load()
    } catch (e) {
      setNotice(errorMessage(e))
    } finally {
      setBusyId(null)
    }
  }

  const change = (e) => setForm((v) => ({ ...v, [e.target.name]: e.target.value }))

  // 이 공고와 연결된 동행 모집 글 작성
  const create = async (e) => {
    e.preventDefault()
    if (!getSession()) {
      navigate('/login')
      return
    }
    setSaving(true)
    setNotice('')
    try {
      await communicationRequest('community/companions/', {
        method: 'POST',
        body: {
          title: form.title.trim(),
          job: Number(jobId),
          capacity: Number(form.capacity),
          meet_place: form.meet_place.trim(),
          meet_at: form.meet_at ? new Date(form.meet_at).toISOString() : null,
        },
      })
      setForm({ title: '', capacity: 2, meet_place: '', meet_at: '' })
      setOpen(false)
      await load()
    } catch (err) {
      setNotice(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const { loading, error, list } = state

  return (
    <section className="cp-section">
      <div className="cp-head">
        <h2 className="jd-heading">이 공고 같이 갈 사람</h2>
        <button
          type="button"
          className="cp-btn ghost cp-new"
          onClick={() => (getSession() ? setOpen((v) => !v) : navigate('/login'))}
        >
          {open ? '닫기' : '동행 모집하기'}
        </button>
      </div>
      {open && (
        <form className="cp-form" onSubmit={create}>
          <label>
            제목
            <input name="title" value={form.title} onChange={change} maxLength={150} required placeholder="예: 천안역에서 같이 출발해요" />
          </label>
          <label>
            모집 인원 (본인 제외)
            <input name="capacity" type="number" min="1" max="20" value={form.capacity} onChange={change} required />
          </label>
          <label>
            만날 장소 (선택)
            <input name="meet_place" value={form.meet_place} onChange={change} maxLength={150} />
          </label>
          <label>
            만날 일시 (선택)
            <input name="meet_at" type="datetime-local" value={form.meet_at} onChange={change} />
          </label>
          <button type="submit" className="cp-btn" disabled={saving || !form.title.trim()}>
            {saving ? '등록 중…' : '등록하기'}
          </button>
        </form>
      )}
      {loading && <p>불러오는 중입니다.</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && list.length === 0 && <p>아직 동행 모집 글이 없습니다.</p>}
      {notice && <p role="alert" className="jd-notice">{notice}</p>}
      <ul className="cp-list">
        {list.map((c) => {
          const full = c.participant_count >= c.capacity
          return (
            <li key={c.id} className="cp-card">
              <strong className="cp-title">{c.title}</strong>
              <span className="cp-info">
                {c.author.name} · {c.author.temperature}°
              </span>
              <span className="cp-info">
                {[c.meet_place, meetLabel(c.meet_at)].filter(Boolean).join(' · ') || '장소·시간 미정'}
              </span>
              <span className="cp-info">
                {c.participant_count}/{c.capacity}명 참여
              </span>
              <button
                type="button"
                className={`cp-btn${c.is_joined ? ' ghost' : ''}`}
                disabled={busyId === c.id || c.is_mine || (full && !c.is_joined)}
                onClick={() => toggleJoin(c)}
              >
                {c.is_mine
                  ? '내가 모집한 글'
                  : c.is_joined
                    ? '참여 취소'
                    : full
                      ? '모집 마감'
                      : '참여하기'}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}