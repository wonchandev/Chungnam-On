import { useCallback, useState } from 'react'
import { Building2, ChevronRight, Crown, Factory, HardHat, Search, Sprout, Truck, User } from 'lucide-react'
import { apiGet, apiRequest } from '../../api/client.js'
import useHomeResource from '../Home/hooks/useHomeResource.js'
import useHomeSession from '../Home/hooks/useHomeSession.js'
import JobCard from '../Home/components/JobCard.jsx'
import DetailDialog from '../Home/components/DetailDialog.jsx'
import LoginDialog from '../Home/components/LoginDialog.jsx'
import ResourceState from '../Home/components/ResourceState.jsx'
import '../Home/styles/home.css'
import './jobs.css'

const QUICK_MENUS = [
  { tab: 'all', label: '일자리 찾기', icon: <Search size={22} aria-hidden="true" /> },
  { tab: 'applications', label: '내 구직활동', icon: <User size={22} aria-hidden="true" /> },
  { tab: 'agencies', label: '인력사무소', icon: <Building2 size={22} aria-hidden="true" /> },
  { tab: 'bookmarks', label: '관심 공고', icon: <Crown size={22} aria-hidden="true" /> },
]
const POPULAR_CATEGORIES = [
  { label: '제조 생산', icon: <Factory size={24} aria-hidden="true" />, code: 'manufacturing' },
  { label: '건설 현장', icon: <HardHat size={24} aria-hidden="true" />, code: 'construction' },
  { label: '농업, 축산', icon: <Sprout size={24} aria-hidden="true" />, code: 'agriculture' },
  { label: '물류,배송', icon: <Truck size={24} aria-hidden="true" />, code: 'logistics' },
]
const TITLES = { all: '일자리 찾기', recommended: '나에게 맞는 일자리', applications: '내 구직활동', agencies: '인력사무소', bookmarks: '관심 공고' }
const STATUS = { pending: '대기', approved: '승인', rejected: '거절' }
const LOGIN_TABS = ['applications', 'bookmarks', 'recommended']

export default function JobsPage() {
  const { session, saveSession, login } = useHomeSession()
  const [tab, setTab] = useState('all')
  const [input, setInput] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [detailId, setDetailId] = useState(null)
  const [loginOpen, setLoginOpen] = useState(false)
  const [saved, setSaved] = useState({})
  const [notice, setNotice] = useState('')
  const needLogin = LOGIN_TABS.includes(tab) && !session
  const options = useCallback((signal) => ({ signal, accessToken: session?.access, refreshToken: session?.refresh, onRefresh: saveSession }), [session, saveSession])

  function choose(next) { setTab(next); setNotice(''); if (next !== 'all') setCategory('') }
  function search(event) { event.preventDefault(); setTab('all'); setCategory(''); setQuery(input.trim()) }
  async function bookmark(job) {
    if (!session) { setLoginOpen(true); return }
    const current = saved[job.id] ?? job.is_bookmarked
    try {
      await apiRequest(`jobs/${job.id}/bookmark/`, { ...options(), method: current ? 'DELETE' : 'POST' })
      setSaved((value) => ({ ...value, [job.id]: !current }))
    } catch (error) { setNotice(error.message) }
  }
  const card = (job, extra) => <div className="jobs-result" key={extra?.key ?? job.id}>
    {extra?.badge && <span className="jobs-status">{extra.badge}</span>}
    <JobCard job={job} onOpen={setDetailId} onBookmark={bookmark} bookmarked={saved[job.id] ?? job.is_bookmarked} />
  </div>

  return (
    <div className="jobs-page">
      <div className="jobs-hero">
        <h1>구인구직</h1>
        <p>충남의 다양한 일자리를<br />한눈에 찾아보세요</p>
      </div>

      <form className="jobs-search" onSubmit={search}>
        <Search size={16} aria-hidden="true" />
        <input type="search" aria-label="일자리 검색" value={input} onChange={(event) => setInput(event.target.value)} placeholder="직종, 지역, 회사 검색" />
      </form>

      <div className="jobs-quick">
        {QUICK_MENUS.map(({ tab: value, label, icon }) => (
          <button key={value} type="button" className={`jobs-quick-item${tab === value ? ' is-active' : ''}`} aria-pressed={tab === value} onClick={() => choose(value)}>
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      <button type="button" className="jobs-ai" onClick={() => choose('recommended')}>
        <span className="jobs-ai-text">
          <span className="jobs-ai-badge">AI 추천</span>
          <strong>내게 맞는 일자리를<br />추천해드려요!</strong>
        </span>
        <ChevronRight size={24} aria-hidden="true" />
      </button>

      <h2 className="jobs-heading">지금 많이 찾는 일자리</h2>
      <div className="jobs-popular">
        {POPULAR_CATEGORIES.map(({ label, icon, code }) => (
          <button key={code} type="button" className={`jobs-popular-item${category === code ? ' is-active' : ''}`} aria-pressed={category === code} onClick={() => { setTab('all'); setCategory(category === code ? '' : code) }}>
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      <h2 className="jobs-heading">{query && tab === 'all' ? `“${query}” 검색 결과` : TITLES[tab]}</h2>
      {needLogin ? <div className="home-state"><p>로그인하면 확인할 수 있어요.</p><button type="button" onClick={() => setLoginOpen(true)}>로그인</button></div>
        : <Results key={`${tab}:${query}:${category}:${session?.access || ''}`} tab={tab} query={query} category={category} options={options} onLogin={() => setLoginOpen(true)} card={card} />}
      <p className="home-notice" role="status">{notice}</p>

      {detailId !== null && <DetailDialog id={detailId} session={session} onClose={() => setDetailId(null)} onRefresh={saveSession} onLogin={() => setLoginOpen(true)} />}
      {loginOpen && <LoginDialog message="로그인이 필요해요." onClose={() => setLoginOpen(false)} onLogin={(tokens) => { login(tokens); setLoginOpen(false) }} />}
    </div>
  )
}

// 탭·검색 조건이 바뀌면 key 로 다시 마운트해, 이전 탭의 데이터로 잘못 그려지지 않게 한다.
function Results({ tab, query, category, options, onLogin, card }) {
  const load = useCallback((signal) => {
    const o = options(signal)
    if (tab === 'applications') return apiGet('applications/mine/', o)
    if (tab === 'agencies') return apiGet('agencies/', o)
    if (tab === 'bookmarks') return apiGet('jobs/bookmarks/', o)
    if (tab === 'recommended') return apiGet('jobs/recommended/', o)
    return apiGet('jobs/', { ...o, query: { q: query, category, ordering: '-created_at' } })
  }, [tab, query, category, options])
  const resource = useHomeResource(load)
  const empty = tab === 'applications' ? '아직 지원한 공고가 없어요.' : tab === 'bookmarks' ? '관심 공고가 없어요. 별 아이콘으로 저장해 보세요.' : '조건에 맞는 공고가 없어요.'
  return <ResourceState resource={resource} onLogin={onLogin} empty={empty}>
    {(items) => tab === 'agencies'
      ? <div className="jobs-agencies">{items.map((agency) => <div className="jobs-agency" key={agency.id}><Building2 size={22} aria-hidden="true" /><div><strong>{agency.name}</strong><small>{agency.address} · 온도 {agency.temperature}° · 후기 {agency.review_count}개</small></div><span>공고 {agency.open_job_count}건</span></div>)}</div>
      : <div className="home-job-list">{items.map((item) => tab === 'applications' ? card(item.job, { key: item.id, badge: STATUS[item.status] || item.status }) : card(item))}</div>}
  </ResourceState>
}
