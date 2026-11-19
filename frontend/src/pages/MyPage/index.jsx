import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ArrowLeft, Bookmark, BriefcaseBusiness, ClipboardCheck, Clock3, LogOut, Settings, ShieldCheck, Thermometer, UserRound } from 'lucide-react'
import useHomeSession from '../Home/hooks/useHomeSession.js'
import useAdminResource from '../Administration/useAdminResource.js'
import ResourceState from './components/ResourceState.jsx'
import ProfileForm from './components/ProfileForm.jsx'
import WorkerProfile from './components/WorkerProfile.jsx'
import SettingsPanel from './components/SettingsPanel.jsx'
import SafetyPanel from './components/SafetyPanel.jsx'
import Reputation from './components/Reputation.jsx'
import { myRequest, rows } from './api.js'
import './mypage.css'

function MemberPage() {
  const { logout } = useHomeSession()
  const [tab, setTab] = useState('profile')
  const [updatedUser, setUpdatedUser] = useState(null)
  const loadSummary = useCallback(signal => myRequest('me/summary/', { signal }), [])
  const loadOptions = useCallback(async signal => {
    const [regions, languages, categories] = await Promise.all([myRequest('regions/', { signal, query: { level: 'sigungu' } }), myRequest('languages/', { signal }), myRequest('categories/', { signal })])
    return { regions: rows(regions), languages: rows(languages), categories: rows(categories) }
  }, [])
  const summary = useAdminResource(loadSummary)
  const options = useAdminResource(loadOptions)
  return <div className="my-page">
    <header className="my-heading"><div><span>MY CHUNGNAM ON</span><h1>마이페이지</h1><p>나의 정보와 일하는 조건을 한곳에서 관리해요.</p></div><Link to="/" className="my-home-link"><ArrowLeft size={16} />홈으로</Link></header>
    <ResourceState resource={summary}>{data => {
      const user = updatedUser || data.profile
      const worker = user.role === 'worker'
      const stats = worker ? [{ label: '지원 대기', value: data.applications?.pending || 0, Icon: Clock3 }, { label: '승인된 지원', value: data.applications?.approved || 0, Icon: ClipboardCheck }, { label: '관심 공고', value: data.bookmark_count, Icon: Bookmark }] : [{ label: '모집 중인 공고', value: data.jobs?.open || 0, Icon: BriefcaseBusiness }, { label: '대기 중인 지원자', value: data.jobs?.pending_applicants || 0, Icon: Clock3 }, { label: '관심 공고', value: data.bookmark_count, Icon: Bookmark }]
      const tabs = [{ id: 'profile', label: '내 정보', Icon: UserRound }, ...(worker ? [{ id: 'worker', label: '근로자 이력', Icon: BriefcaseBusiness }] : []), { id: 'settings', label: '설정', Icon: Settings }, { id: 'safety', label: '신고·차단', Icon: ShieldCheck }]
      return <>
        <div className="my-overview"><div className="my-person"><span className="my-avatar">{user.profile_image ? <img src={user.profile_image} alt="내 프로필" /> : <UserRound size={34} strokeWidth={1.6} />}</span><div><span className="my-role">{worker ? '근로자' : user.company?.is_agency ? '인력사무소' : '사업주'}</span><h2>{user.name || user.company?.name || user.username}<small>님</small></h2><p>@{user.username}</p></div></div><div className="my-temperature"><span><Thermometer size={18} />나의 온도</span><strong>{Number(user.temperature).toFixed(1)}<small>°</small></strong><p>함께 일한 경험이 온도에 반영돼요.</p></div></div>
        <div className="my-stats">{stats.map(item => <div key={item.label}><item.Icon size={19} aria-hidden="true" /><strong>{item.value || 0}<small>건</small></strong><span>{item.label}</span></div>)}</div>
        <nav className="my-tabs" aria-label="마이페이지 메뉴">{tabs.map(item => <button key={item.id} type="button" aria-pressed={tab === item.id} onClick={() => setTab(item.id)}><item.Icon size={17} aria-hidden="true" />{item.label}</button>)}</nav>
        {['profile', 'worker', 'settings'].includes(tab) && <ResourceState resource={options}>{choices => <>
          {tab === 'profile' && <><ProfileForm user={user} regions={choices.regions} onSaved={setUpdatedUser} /><Reputation userId={user.id} /></>}
          {tab === 'worker' && worker && <WorkerProfile categories={choices.categories} regions={choices.regions} />}
          {tab === 'settings' && <SettingsPanel user={user} languages={choices.languages} onSaved={setUpdatedUser} />}
        </>}</ResourceState>}
        {tab === 'safety' && <SafetyPanel />}
        <footer className="my-footer"><span>CHUNGNAM ON · 나의 일과 생활을 연결하다</span><button type="button" onClick={logout}><LogOut size={15} />로그아웃</button></footer>
      </>
    }}</ResourceState>
  </div>
}
export default function MyPage() {
  const { session } = useHomeSession()
  useEffect(() => { document.title = '마이페이지 | 충남온'; return () => { document.title = '충남온 | 일자리와 생활을 연결하다' } }, [])
  return session ? <MemberPage /> : <Navigate to="/login" replace state={{ from: '/mypage' }} />
}
