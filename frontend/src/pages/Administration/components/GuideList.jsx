import { useCallback, useState } from 'react'
import { ChevronRight, FileText, Search } from 'lucide-react'
import FormSelect from '../../../components/FormSelect.jsx'
import useAdminResource from '../useAdminResource.js'
import { adminRequest, guideCategories, rows } from '../api.js'
import ResourceState from './ResourceState.jsx'

export default function GuideList({ mode = 'guides', initialCategory = '', initialSearch = '', onOpen }) {
  const [filters, setFilters] = useState({ category: initialCategory, search: initialSearch, page: 1 })
  const [draft, setDraft] = useState(initialSearch)
  const load = useCallback(signal => adminRequest(`admin-info/${mode}/`, { signal, query: mode === 'guides' ? filters : { limit: 50 } }), [mode, filters])
  const resource = useAdminResource(load)
  const title = mode === 'frequent' ? '자주 찾는 정보' : mode === 'popular' ? '최근 인기 정보' : '행정 서비스 안내'
  function filter(name, value) { setFilters(current => ({ ...current, [name]: value, page: 1 })) }
  return <section className="admin-panel" aria-label={title}>
    <div className="admin-section-heading"><h2>{title}</h2>{mode === 'popular' && <span>최근 7일 조회 기준</span>}{mode === 'frequent' && <span>누적 조회 기준</span>}</div>
    {mode === 'guides' && <div className="admin-guide-filters">
      <FormSelect name="category" label="분야" value={filters.category} onChange={event => filter('category', event.target.value)} options={guideCategories} />
      <form className="admin-search" onSubmit={event => { event.preventDefault(); filter('search', draft.trim()) }}><label className="home-sr-only" htmlFor="admin-guide-search">행정 정보 검색</label><input id="admin-guide-search" value={draft} onChange={event => setDraft(event.target.value)} placeholder="궁금한 행정 정보를 검색하세요" /><button aria-label="검색"><Search size={20} /></button></form>
    </div>}
    <ResourceState resource={resource}>{data => <>
      {!rows(data).length ? <p className="admin-state">{mode === 'popular' ? '최근 조회된 안내가 아직 없어요.' : '조건에 맞는 안내가 없어요.'}</p> : <div className="admin-guide-list">{rows(data).map(guide => <button key={guide.id} className="admin-guide-row" onClick={() => onOpen(guide.id)}>
        <span className="admin-row-icon"><FileText size={21} aria-hidden="true" /></span><span className="admin-row-content"><small>{guide.category_label}</small><strong>{guide.title}</strong><span>{guide.summary || '안내 내용을 확인하세요.'}</span></span><ChevronRight size={19} aria-hidden="true" />
      </button>)}</div>}
      {mode === 'guides' && data?.count > 20 && <div className="admin-pagination"><button disabled={filters.page === 1 || resource.loading} onClick={() => setFilters(current => ({ ...current, page: current.page - 1 }))}>이전</button><span>{filters.page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next || resource.loading} onClick={() => setFilters(current => ({ ...current, page: current.page + 1 }))}>다음</button></div>}
    </>}</ResourceState>
  </section>
}
