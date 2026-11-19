import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { apiRequest } from '../../api/client.js'
import { getSession, saveSession } from '../../api/session.js'

const STATUS_LABELS = {
  pending: '대기',
  approved: '승인',
  rejected: '거절',
  completed: '완료',
}

export default function MyLists({ kind }) {
  const navigate = useNavigate()
  const session = getSession()
  const isApplications = kind === 'applications'
  const [state, setState] = useState({ loading: !!session, error: '', items: [] })

  useEffect(() => {
    if (!session) return undefined
    const controller = new AbortController()
    apiRequest(isApplications ? 'applications/mine/' : 'jobs/bookmarks/', {
      signal: controller.signal,
      accessToken: session.access,
      refreshToken: session.refresh,
      onRefresh: saveSession,
    })
      .then((data) => {
        const items = Array.isArray(data) ? data : data.results
        setState({ loading: false, error: '', items })
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState({ loading: false, error: e.message, items: [] })
        }
      })
    return () => controller.abort()
  }, [isApplications]) // eslint-disable-line react-hooks/exhaustive-deps

  const title = isApplications ? '내 구직활동' : '관심 공고'

  return (
    <div className="jl-page">
      <button type="button" className="jl-back" onClick={() => navigate(-1)}>
        <ChevronLeft size={20} aria-hidden="true" /> {title}
      </button>

      {!session && (
        <p>
          로그인이 필요합니다. <Link to="/login">로그인하기</Link>
        </p>
      )}
      {session && state.loading && <p>불러오는 중입니다.</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {session && !state.loading && !state.error && state.items.length === 0 && (
        <p>{isApplications ? '지원한 공고가 없습니다.' : '관심 공고가 없습니다.'}</p>
      )}

      <ul className="jl-list">
        {state.items.map((item) => {
          const job = item.job ?? item
          return (
            <li key={item.id}>
              <Link to={`/jobs?id=${job.id}`} className="jl-card">
                <strong className="jl-title">{job.title}</strong>
                {isApplications && (
                  <span className="jl-pay">{STATUS_LABELS[item.status] ?? item.status}</span>
                )}
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
