import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Star } from 'lucide-react'
import { getSession } from '../../api/session.js'
import { communicationRequest, errorMessage, items } from '../Communication/api.js'
import ChatDialog from '../Communication/components/ChatDialog.jsx'
import { payLabel, timeLabel } from './format.js'
import './detail.css'

const TAG_LABELS = {
  beginner_ok: '초보가능',
  with_friend: '친구와 함께',
  lunch_provided: '점심 제공',
  local_preferred: '인근지역우대',
  night_shift: '야간근무',
}

const APPLY_LABELS = {
  pending: '지원 완료 (대기 중)',
  approved: '지원 승인됨',
  rejected: '지원 거절됨',
  completed: '근무 완료',
}

export default function JobDetail({ id }) {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', job: null })
  const [marked, setMarked] = useState(false)
  const [applied, setApplied] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [room, setRoom] = useState(null)
  const [languages, setLanguages] = useState([])

  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true, error: '', job: null })
    communicationRequest(`jobs/${id}/`, { signal: controller.signal })
      .then((job) => {
        setState({ loading: false, error: '', job })
        setMarked(job.is_bookmarked)
        setApplied(job.my_application_status)
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState({ loading: false, error: e.message, job: null })
        }
      })
    return () => controller.abort()
  }, [id])

  const { loading, error, job } = state
  const tags = job ? Object.keys(TAG_LABELS).filter((k) => job.tags[k]) : []

  const requireLogin = () => {
    if (getSession()) return true
    navigate('/login')
    return false
  }

  const openChat = async (roomId) => {
    if (!languages.length) {
      setLanguages(items(await communicationRequest('languages/')))
    }
    setRoom({ id: roomId })
  }

  const toggleBookmark = async () => {
    if (!requireLogin()) return
    const next = !marked
    setMarked(next)
    try {
      await communicationRequest(`jobs/${id}/bookmark/`, { method: next ? 'POST' : 'DELETE' })
    } catch {
      setMarked(!next)
    }
  }

  const apply = async () => {
    if (!requireLogin()) return
    setBusy(true)
    setNotice('')
    try {
      const res = await communicationRequest(`jobs/${id}/apply/`, { method: 'POST', body: {} })
      setApplied(res?.status || 'pending')
      if (res?.chat_room_id) await openChat(res.chat_room_id)
    } catch (e) {
      setNotice(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const inquire = async () => {
    if (!requireLogin()) return
    setBusy(true)
    setNotice('')
    try {
      const chat = await communicationRequest('chat/rooms/', {
        method: 'POST',
        body: { job_id: Number(id) },
      })
      await openChat(chat.id)
    } catch (e) {
      setNotice(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="jd-page">
      <button type="button" className="jl-back" onClick={() => navigate(-1)}>
        <ChevronLeft size={20} aria-hidden="true" /> 채용 공고
      </button>
      {loading && <p>불러오는 중입니다.</p>}
      {error && <p role="alert">{error}</p>}
      {job && (
        <>
          <div className="jd-top">
            <span className="jd-badge">{job.pay_type === 'daily' ? '일급' : '시급'}</span>
            <button
              type="button"
              className={`jd-star${marked ? ' on' : ''}`}
              onClick={toggleBookmark}
              aria-label={marked ? '관심 공고 해제' : '관심 공고 등록'}
            >
              <Star size={24} fill={marked ? 'currentColor' : 'none'} />
            </button>
          </div>
          <h1 className="jd-title">{job.title}</h1>
          <p className="jd-company">
            {job.company.name}
            {job.company.is_verified && ' · 인증 사업주'} · {job.company.temperature}°
          </p>

          <div className="jd-summary">
            <span>{job.region.name}</span>
            <span>{job.start_date}</span>
            <span>{job.duration_days}일</span>
            <span>{job.pay_amount.toLocaleString()}원</span>
          </div>

          {tags.length > 0 && (
            <div className="jd-tags">
              {tags.map((k) => (
                <span key={k}>{TAG_LABELS[k]}</span>
              ))}
            </div>
          )}

          <h2 className="jd-heading">근무 조건</h2>
          <dl className="jd-rows">
            <div><dt>직무</dt><dd>{job.work_type}</dd></div>
            <div><dt>모집 인원</dt><dd>{job.headcount}명</dd></div>
            <div>
              <dt>근무 시간</dt>
              <dd>
                {timeLabel(job)}
                {job.break_minutes > 0 && ` (휴게 ${job.break_minutes / 60}시간)`}
              </dd>
            </div>
            <div><dt>근무 기간</dt><dd>{job.start_date}부터 {job.duration_days}일</dd></div>
            <div><dt>급여</dt><dd>{payLabel(job)}</dd></div>
          </dl>

          {job.description && (
            <>
              <h2 className="jd-heading">상세 내용</h2>
              <p className="jd-desc">{job.description}</p>
            </>
          )}

          {notice && <p role="alert" className="jd-notice">{notice}</p>}

          {!job.is_owner && (
            <div className="jd-actions">
              <button type="button" className="jd-btn ghost" onClick={inquire} disabled={busy}>
                문의하기
              </button>
              <button
                type="button"
                className="jd-btn"
                onClick={apply}
                disabled={busy || !!applied}
              >
                {applied ? APPLY_LABELS[applied] || '지원 완료' : '지원하기'}
              </button>
            </div>
          )}
        </>
      )}

      {room && (
        <ChatDialog initialRoom={room} languages={languages} onClose={() => setRoom(null)} />
      )}
    </div>
  )
}