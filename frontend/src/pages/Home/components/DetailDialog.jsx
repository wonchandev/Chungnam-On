import { useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { homeApi } from '../api/home.js'
import useHomeResource from '../hooks/useHomeResource.js'
import { money, payLabel } from '../utils/formatters.js'
import HomeDialog from './HomeDialog.jsx'

export default function DetailDialog({ id, session, onClose, onRefresh }) {
  const load = useCallback((signal) => homeApi.detail(id, { signal, accessToken: session?.access, refreshToken: session?.refresh, onRefresh }), [id, session, onRefresh])
  const resource = useHomeResource(load)
  const job = resource.data
  return <HomeDialog title="일자리 상세" onClose={onClose} wide>
    {resource.loading ? <p role="status">공고를 불러오고 있어요…</p> : resource.error ? <div role="alert"><p>{resource.error.message}</p><button type="button" onClick={resource.retry}>다시 시도</button></div> : <>
      <span className="home-company">{job.company_name}</span><h3 className="home-detail-title">{job.title}</h3>
      <strong className="home-detail-pay">{payLabel(job.pay_type)} {money(job.pay_amount)}원</strong>
      <dl className="home-detail-info">
        <dt>근무지</dt><dd>{job.address || job.region?.name}</dd>
        <dt>근무 날짜</dt><dd>{job.start_date}{job.end_date && job.end_date !== job.start_date ? ` ~ ${job.end_date}` : ''}</dd>
        <dt>근무 시간</dt><dd>{job.start_time?.slice(0, 5)} ~ {job.end_time?.slice(0, 5)} (휴게 {job.break_minutes}분)</dd>
        <dt>모집 인원</dt><dd>{job.headcount}명</dd>
        <dt>사업주 온도</dt><dd>{job.company_temperature}°</dd>
      </dl>
      <p className="home-detail-description">{job.description || '상세 설명이 등록되지 않았어요.'}</p>
      <Link className="home-primary home-detail-link" to="/jobs" onClick={onClose}>구인구직으로 이동<ArrowRight size={17} /></Link>
    </>}
  </HomeDialog>
}
