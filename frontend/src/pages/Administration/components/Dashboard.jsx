import { useCallback } from 'react'
import { BriefcaseBusiness, CalendarDays, ChevronRight, ClipboardCheck, FileCheck2, FileText, House, PenLine, ShieldCheck } from 'lucide-react'
import useAdminResource from '../useAdminResource.js'
import { adminRequest, rows } from '../api.js'
import ResourceState from './ResourceState.jsx'
import ComplaintList from './ComplaintList.jsx'

const shortcuts = [
  { title: '비자·체류', category: 'visa', Icon: BriefcaseBusiness },
  { title: '근로계약', category: 'labor', Icon: PenLine },
  { title: '증명서 안내', search: '증명', Icon: FileCheck2 },
  { title: '체류지 변경', category: 'visa', search: '체류지', Icon: House },
  { title: '보험 안내', category: 'insurance', Icon: ShieldCheck },
  { title: '각종 신고', search: '신고', Icon: FileText },
]
export default function Dashboard({ session, onBrowse, onOpenGuide, onOpenComplaint, onLogin, revision }) {
  const loadGuides = useCallback(signal => adminRequest('admin-info/guides/', { signal, query: { ordering: '-view_count' } }), [])
  const loadStats = useCallback(signal => adminRequest('admin-info/dashboard/', { signal }), [])
  const guides = useAdminResource(loadGuides)
  const stats = useAdminResource(loadStats)
  return <>
    <div className="admin-hero"><div><h2>행정 서비스를<br />간편하게 알아보세요</h2><p>비자·체류, 근로계약 등<br />필요한 행정 정보를 한곳에서 확인하세요.</p></div><div className="admin-hero-art" aria-hidden="true"><ClipboardCheck size={76} strokeWidth={1.5} /><span><ShieldCheck size={29} /></span></div></div>
    <div className="admin-shortcuts" aria-label="행정 정보 분야">{shortcuts.map(item => <button key={item.title} onClick={() => onBrowse({ category: item.category || '', search: item.search || '' })}><span><item.Icon size={29} strokeWidth={1.8} aria-hidden="true" /></span><strong>{item.title}</strong></button>)}</div>
    <section className="admin-panel"><div className="admin-section-heading"><h2>행정 서비스</h2><button className="admin-text-button" onClick={() => onBrowse({})} aria-label="행정 서비스 전체 보기"><ChevronRight size={20} /></button></div>
      <ResourceState resource={guides}>{data => rows(data).length ? <div className="admin-service-list">{rows(data).slice(0, 3).map(guide => <button key={guide.id} className="admin-service-row" onClick={() => onOpenGuide(guide.id)}>
        <span className="admin-row-icon">{guide.category === 'insurance' ? <ShieldCheck size={23} /> : guide.category === 'visa' ? <CalendarDays size={23} /> : <FileText size={23} />}</span><span className="admin-row-content"><strong>{guide.title}</strong><span>{guide.summary}</span></span><ChevronRight size={17} aria-hidden="true" />
      </button>)}</div> : <p className="admin-state">등록된 행정 안내가 없어요.</p>}</ResourceState>
      <button className="admin-more" onClick={() => onBrowse({})}>더보기</button>
    </section>
    <section className="admin-panel"><div className="admin-section-heading"><h2>진행 중인 문의</h2><button className="admin-text-button" onClick={() => onOpenComplaint()} aria-label="내 민원 전체 보기"><ChevronRight size={20} /></button></div>
      {session ? <ComplaintList key={revision} preview onOpen={onOpenComplaint} /> : <div className="admin-login-prompt"><p>로그인하면 접수한 문의와 처리 상태를 확인할 수 있어요.</p><button className="admin-secondary" onClick={onLogin}>로그인</button></div>}
    </section>
    {stats.data && <p className="admin-dashboard-caption">등록된 행정 안내 {Number(stats.data.guides_total).toLocaleString('ko-KR')}건 · 함께하는 근로자 {Number(stats.data.total_workers).toLocaleString('ko-KR')}명</p>}
    {stats.error && <p className="admin-dashboard-caption">통계를 불러오지 못했어요. <button className="admin-text-button" onClick={stats.retry}>다시 시도</button></p>}
  </>
}
