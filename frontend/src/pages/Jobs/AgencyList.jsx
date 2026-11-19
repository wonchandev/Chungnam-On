import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { apiGet } from '../../api/client.js'

export default function AgencyList() {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', agencies: [] })

  useEffect(() => {
    const controller = new AbortController()
    apiGet('agencies/', { signal: controller.signal })
      .then((data) => setState({ loading: false, error: '', agencies: data.results }))
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState({ loading: false, error: e.message, agencies: [] })
        }
      })
    return () => controller.abort()
  }, [])

  return (
    <div className="jl-page">
      <button type="button" className="jl-back" onClick={() => navigate(-1)}>
        <ChevronLeft size={20} aria-hidden="true" /> 인력사무소
      </button>
      {state.loading && <p>불러오는 중입니다.</p>}
      {state.error && <p role="alert">{state.error}</p>}
      {!state.loading && !state.error && state.agencies.length === 0 && (
        <p>등록된 인력사무소가 없습니다.</p>
      )}
      <ul className="jl-list">
        {state.agencies.map((a) => (
          <li key={a.id} className="jl-card">
            <strong className="jl-title">
              {a.name}
              {a.is_verified && <em className="ag-verified">인증</em>}
            </strong>
            <span className="jl-info">{a.address}</span>
            <span className="jl-info">
              온도 {a.temperature}° · 후기 {a.review_count}건
            </span>
            <span className="jl-pay">모집 중 공고 {a.open_job_count}건</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
