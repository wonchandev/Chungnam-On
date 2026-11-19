import { useCallback, useRef, useState } from 'react'
import { Flame, ThumbsUp } from 'lucide-react'
import { apiRequest } from '../../../api/client.js'
import { homeApi } from '../api/home.js'
import useHomeResource from '../hooks/useHomeResource.js'
import { rows } from '../utils/formatters.js'
import ResourceState from './ResourceState.jsx'
import JobCard from './JobCard.jsx'
import JobTicker from './JobTicker.jsx'

export default function HomeFeed({ region, query, session, onOpen, onLogin, onRefresh }) {
  const [saved, setSaved] = useState({})
  const pendingIds = useRef(new Set())
  const [busyIds, setBusyIds] = useState(new Set())
  const [notice, setNotice] = useState('')
  const options = useCallback((signal) => ({ signal, accessToken: session?.access, refreshToken: session?.refresh, onRefresh }), [session, onRefresh])
  const tickerLoad = useCallback((signal) => region
    ? homeApi.jobs({ region, ordering: '-created_at' }, options(signal)).then((data) => rows(data).slice(0, 3).map((job) => ({ ...job, region: job.region.name })))
    : homeApi.ticker(options(signal)), [region, options])
  const urgentLoad = useCallback((signal) => region
    ? homeApi.jobs({ region, urgent: true, ordering: 'deadline' }, options(signal)).then(rows)
    : homeApi.urgent(options(signal)), [region, options])
  const recommendedLoad = useCallback((signal) => region || query
    ? homeApi.jobs({ region, q: query, ordering: '-created_at' }, options(signal)).then(rows)
    : session ? homeApi.recommended(options(signal)) : homeApi.jobs({ ordering: '-created_at' }, options(signal)).then(rows), [region, query, options, session])
  const ticker = useHomeResource(tickerLoad)
  const urgent = useHomeResource(urgentLoad)
  const recommended = useHomeResource(recommendedLoad)

  async function bookmark(job) {
    if (!session) { onLogin(); return }
    if (pendingIds.current.has(job.id)) return
    const current = saved[job.id] ?? job.is_bookmarked
    pendingIds.current.add(job.id)
    setBusyIds(new Set(pendingIds.current))
    setNotice('')
    try {
      await apiRequest(`jobs/${job.id}/bookmark/`, { ...options(), method: current ? 'DELETE' : 'POST' })
      setSaved((value) => ({ ...value, [job.id]: !current }))
    } catch (error) {
      if (error.status === 401) onLogin()
      else setNotice(error.message)
    } finally {
      pendingIds.current.delete(job.id)
      setBusyIds(new Set(pendingIds.current))
    }
  }

  return <>
    <JobTicker resource={ticker} onLogin={onLogin} onOpen={onOpen} />
    <a className="home-recommend-button" href="#home-recommended">{session ? '나를 위한 추천 일자리' : '새로 올라온 일자리 둘러보기'}</a>
    <section className="home-section home-urgent" aria-labelledby="urgent-title">
      <h2 id="urgent-title"><Flame size={20} aria-hidden="true" />긴급 채용중</h2>
      <ResourceState resource={urgent} onLogin={onLogin} empty="현재 긴급 채용 공고가 없어요.">{(jobs) => <div className="home-urgent-list">{jobs.map((job) => <JobCard key={job.id} job={job} urgent onOpen={onOpen} />)}</div>}</ResourceState>
    </section>
    <section className="home-section home-recommended" id="home-recommended" aria-labelledby="recommended-title">
      <h2 id="recommended-title"><ThumbsUp size={20} aria-hidden="true" />{query ? `“${query}” 검색 결과` : region ? '우리 지역 일자리' : session ? '나에게 딱 맞는 일자리' : '새로 올라온 일자리'}</h2>
      <ResourceState resource={recommended} onLogin={onLogin} empty={query ? '검색 결과가 없어요. 다른 검색어를 입력해 주세요.' : '아직 등록된 일자리가 없어요.'}>{(jobs) => <div className="home-job-list">{jobs.map((job) => <JobCard key={job.id} job={job} onOpen={onOpen} onBookmark={bookmark} busy={busyIds.has(job.id)} bookmarked={saved[job.id] ?? job.is_bookmarked} />)}</div>}</ResourceState>
      <p className="home-notice" role="status">{notice}</p>
    </section>
  </>
}
