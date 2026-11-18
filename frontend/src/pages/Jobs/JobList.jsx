import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { apiRequest } from '../../api/client.js'
import { getSession, saveSession } from '../../api/session.js'
import { payLabel, timeLabel } from './format.js'

export default function JobList({ category, q, recommended }) {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', jobs: [], count: 0 })

  useEffect(() => {
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: '' }))
    const session = getSession()
    apiRequest(recommended ? 'jobs/recommended/' : 'jobs/', {
      signal: controller.signal,
      query: { category, q },
      accessToken: session?.access,
      refreshToken: session?.refresh,
      onRefresh: saveSession,
    })
      .then((data) => {
        const jobs = Array.isArray(data) ? data : data.results
        setState({ loading: false, error: '', jobs, count: data.count ?? jobs.length })
      })
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState((s) => ({ ...s, loading: false, error: e.message }))
        }
      })
    return () => controller.abort()
  }, [category, q, recommended])

  return (
    <div className="jl-page">
      <button type="button" className="jl-back" onClick={() => navigate(-1)}>
        <ChevronLeft size={20} aria-hidden="true" /> 뒤로
      </button>
      {state.loading && <p>불러오는 중입니다.</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {!state.loading && !state.error && (
        <>
          <p className="jl-total">총 {state.count}건</p>
          {state.jobs.length === 0 && <p>조건에 맞는 공고가 없습니다.</p>}
          <ul className="jl-list">
            {state.jobs.map((job) => (
              <li key={job.id}>
                <Link to={`/jobs?id=${job.id}`} className="jl-card">
                  <span className="jl-company">{job.company_name}</span>
                  <strong className="jl-title">
                    {job.is_urgent && <em className="jl-urgent">긴급</em>}
                    {job.title}
                  </strong>
                  <span className="jl-info">
                    {job.region.name} · {timeLabel(job)}
                  </span>
                  <span className="jl-pay">{payLabel(job)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}