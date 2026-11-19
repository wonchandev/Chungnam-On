import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSession } from '../../api/session.js'
import { communicationRequest, errorMessage, items } from '../Communication/api.js'

const meetLabel = (value) =>
  new Date(value).toLocaleString('ko-KR', {
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

  const load = useCallback(
    (signal) =>
      communicationRequest('community/companions/', { signal, query: { status: 'open' } })
        .then((data) =>
          setState({
            loading: false,
            error: '',
            list: items(data).filter((c) => String(c.job) === String(jobId)),
          }),
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

  const { loading, error, list } = state

  return (
    <section className="cp-section">
      <h2 className="jd-heading">이 공고 같이 갈 사람</h2>
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
                {c.meet_place} · {meetLabel(c.meet_at)}
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