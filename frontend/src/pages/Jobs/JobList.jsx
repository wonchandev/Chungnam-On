import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { apiGet } from '../../api/client.js'
import { payLabel, timeLabel } from './format.js'

export default function JobList({ category, q }) {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', jobs: [], count: 0 })

  useEffect(() => {
    const controller = new AbortController()
    setState((s) => ({ ...s, loading: true, error: '' }))
    apiGet('jobs/', { signal: controller.signal, query: { category, q } })
      .then((data) =>
        setState({ loading: false, error: '', jobs: data.results, count: data.count }),
      )
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState((s) => ({ ...s, loading: false, error: e.message }))
        }
      })
    return () => controller.abort()
  }, [category, q])

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