import { useEffect, useState } from 'react'
import { ArrowLeft, Plus } from 'lucide-react'
import useHomeSession from '../Home/hooks/useHomeSession.js'
import LoginDialog from '../Home/components/LoginDialog.jsx'
import Dashboard from './components/Dashboard.jsx'
import GuideList from './components/GuideList.jsx'
import GuideDialog from './components/GuideDialog.jsx'
import ComplaintList from './components/ComplaintList.jsx'
import ComplaintDialog from './components/ComplaintDialog.jsx'
import Notifications from './components/Notifications.jsx'
import AssistantWidget from './chatbot/AssistantWidget.jsx'
import './administration.css'

const tabs = [{ id: 'dashboard', label: '대시보드' }, { id: 'frequent', label: '자주 찾는' }, { id: 'popular', label: '최근 인기' }, { id: 'complaints', label: '민원' }]
export default function AdministrationPage() {
  const { session, login } = useHomeSession()
  const [view, setView] = useState('dashboard')
  const [filters, setFilters] = useState({})
  const [guideId, setGuideId] = useState(null)
  const [complaint, setComplaint] = useState(null)
  const [revision, setRevision] = useState(0)
  const [loginOpen, setLoginOpen] = useState(false)
  const [pending, setPending] = useState(null)
  const [notice, setNotice] = useState('')
  useEffect(() => {
    document.title = '행정관리 | 충남온'
    return () => { document.title = '충남온 | 일자리와 생활을 연결하다' }
  }, [])
  function browse(nextFilters) { setFilters(nextFilters); setView('guides'); setNotice('') }
  function openComplaint(id) {
    if (!id) { setView('complaints'); return }
    if (!session) { setPending({ id }); setLoginOpen(true); return }
    setComplaint({ id })
  }
  function createComplaint() {
    if (!session) { setPending({ create: true }); setLoginOpen(true); return }
    setComplaint({ create: true })
  }
  return <div className="admin-page">
    <header className="admin-page-heading"><button type="button" className="admin-back" aria-label="행정관리 대시보드로 돌아가기" onClick={() => { setView('dashboard'); setFilters({}); setNotice('') }}><ArrowLeft size={21} /></button><h1>행정관리</h1><Notifications session={session} onLogin={() => { setPending(null); setLoginOpen(true) }} onComplaint={openComplaint} /></header>
    <nav className="admin-tabs" aria-label="행정관리 메뉴">{tabs.map(tab => <button key={tab.id} aria-pressed={view === tab.id} onClick={() => { setView(tab.id); setNotice('') }}>{tab.label}</button>)}</nav>
    {notice && <p className="admin-success" role="status">{notice}</p>}
    {view === 'dashboard' && <Dashboard session={session} onBrowse={browse} onOpenGuide={setGuideId} onOpenComplaint={openComplaint} onLogin={() => { setPending(null); setLoginOpen(true) }} revision={revision} />}
    {['guides', 'frequent', 'popular'].includes(view) && <GuideList key={`${view}:${filters.category || ''}:${filters.search || ''}`} mode={view} initialCategory={filters.category || ''} initialSearch={filters.search || ''} onOpen={setGuideId} />}
    {view === 'complaints' && <section className="admin-panel"><div className="admin-section-heading"><h2>민원·문의</h2><button className="admin-primary admin-small-button" onClick={createComplaint}><Plus size={16} aria-hidden="true" />문의 접수</button></div><p className="admin-info-note">충남온 운영자에게 문의하고 답변을 확인하세요. 정부기관의 공식 행정 신청과는 별개입니다.</p>
      {session ? <ComplaintList key={revision} onOpen={openComplaint} /> : <div className="admin-login-prompt"><p>로그인하면 내 문의와 처리 상태를 확인할 수 있어요.</p><button className="admin-secondary" onClick={() => { setPending(null); setLoginOpen(true) }}>로그인</button></div>}
    </section>}
    {guideId && <GuideDialog key={guideId} id={guideId} onClose={() => setGuideId(null)} />}
    {session && complaint && <ComplaintDialog key={complaint.id || 'create'} id={complaint.id} onClose={() => setComplaint(null)} onSaved={id => { setRevision(value => value + 1); setNotice('문의가 접수되었습니다. 민원 탭에서 처리 상태를 확인할 수 있어요.'); setComplaint({ id }) }} />}
    {loginOpen && <LoginDialog message="내 민원과 알림을 확인하려면 로그인해 주세요." onClose={() => { setLoginOpen(false); setPending(null) }} onLogin={tokens => { login(tokens); setLoginOpen(false); if (pending) setComplaint(pending); setPending(null) }} />}
    <AssistantWidget onGuide={setGuideId} />
  </div>
}
