import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { apiGet } from '../../api/client.js'
import { payLabel, timeLabel } from './format.js'

const TAG_LABELS = {
  beginner_ok: '초보가능',
  with_friend: '친구와 함께',
  lunch_provided: '점심 제공',
  local_preferred: '인근지역우대',
  night_shift: '야간근무',
}

export default function JobDetail({ id }) {
  const navigate = useNavigate()
  const [state, setState] = useState({ loading: true, error: '', job: null })

  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true, error: '', job: null })
    apiGet(`jobs/${id}/`, { signal: controller.signal })
      .then((job) => setState({ loading: false, error: '', job }))
      .catch((e) => {
        if (e.name !== 'AbortError') {
          setState({ loading: false, error: e.message, job: null })
        }
      })
    return () => controller.abort()
  }, [id])

  const { loading, error, job } = state
  const tags = job ? Object.keys(TAG_LABELS).filter((k) => job.tags[k]) : []

  return (
    <div className="jd-page">
      <button type="button" className="jl-back" onClick={() => navigate(-1)}>
        <ChevronLeft size={20} aria-hidden="true" /> 채용 공고
      </button>
      {loading && <p>불러오는 중입니다.</p>}
      {error && <p role="alert">{error}</p>}
      {job && (
        <>
          <span className="jd-badge">{job.pay_type === 'daily' ? '일급' : '시급'}</span>
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
        </>
      )}
    </div>
  )
}