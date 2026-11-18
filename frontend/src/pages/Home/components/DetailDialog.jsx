import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageCircle } from 'lucide-react'
import { homeApi } from '../api/home.js'
import useHomeResource from '../hooks/useHomeResource.js'
import { money, payLabel } from '../utils/formatters.js'
import HomeDialog from './HomeDialog.jsx'
import JobCompanions from './JobCompanions.jsx'

export default function DetailDialog({ id, session, onClose, onRefresh, onLogin }) {
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(null)
  const [error, setError] = useState('')
  const options = useCallback((signal) => ({ signal, accessToken: session?.access, refreshToken: session?.refresh, onRefresh }), [session, onRefresh])
  const load = useCallback((signal) => homeApi.detail(id, options(signal)), [id, options])
  const resource = useHomeResource(load)
  const job = resource.data

  function goChat(roomId) { onClose(); navigate('/communication', { state: { roomId } }) }
  async function run(action) {
    if (!session) { onLogin?.(); return }
    setBusy(true); setError('')
    try { await action() } catch (failure) {
      if (failure.status === 401) onLogin?.()
      else setError(failure.message)
    } finally { setBusy(false) }
  }
  const apply = () => run(async () => { setDone(await homeApi.apply(id, options())) })
  const inquire = () => run(async () => { goChat((await homeApi.openRoom(id, options())).id) })

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
      <JobCompanions job={job} session={session} options={options} onLogin={() => onLogin?.()} />
      {done ? <div className="home-apply-done" role="status"><strong>지원이 완료됐어요.</strong><p>사장님이 확인하면 알림으로 알려드려요.</p>{done.chat_room_id && <button type="button" className="home-primary" onClick={() => goChat(done.chat_room_id)}><MessageCircle size={17} aria-hidden="true" />사장님과 대화하기</button>}</div>
        : <div className="home-detail-actions">
          <button type="button" className="home-secondary" onClick={inquire} disabled={busy}>문의하기</button>
          <button type="button" className="home-primary" onClick={apply} disabled={busy || job.status !== 'open'}>{busy ? '처리 중…' : '지원하기'}</button>
        </div>}
      {error && <p className="home-notice" role="alert">{error}</p>}
    </>}
  </HomeDialog>
}
