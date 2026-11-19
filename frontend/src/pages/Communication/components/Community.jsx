import { useCallback, useState } from 'react'
import { Heart, MessageCircle, Plus, Users } from 'lucide-react'
import FormSelect from '../../../components/FormSelect.jsx'
import useResource from '../../Administration/useAdminResource.js'
import { communicationRequest, items } from '../api.js'
import CommunityEditor from './CommunityEditor.jsx'
import CommunityDetail from './CommunityDetail.jsx'
import SegmentedControl from './SegmentedControl.jsx'
import { categories, dateLabel } from './communityHelpers.js'
import Pagination from './CommunityPagination.jsx'

export default function Community({ session, onLogin }) {
  const [kind, setKind] = useState('posts')
  const [region, setRegion] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [editor, setEditor] = useState(null)
  const [selected, setSelected] = useState(null)
  const loadRegions = useCallback(signal => communicationRequest('regions/', { signal, query: { level: 'sigungu' } }), [])
  const regions = useResource(loadRegions)
  const load = useCallback(signal => communicationRequest(`community/${kind}/`, { signal, accessToken: session?.access, query: { page, region: region || undefined, ...(kind === 'posts' ? { category: category || undefined, q: query || undefined } : { status: status || undefined }) } }), [kind, region, category, status, query, page, session?.access])
  const resource = useResource(load)
  const regionOptions = [{ value: '', label: '충남 전체' }, ...items(regions.data).map(item => ({ value: item.code, label: item.name }))]
  function change(setter, value) { setter(value); setPage(1) }
  return <section className="comm-community" aria-label="커뮤니티">
    <div className="comm-section-heading"><div><h2>함께 나누는 충남 생활</h2><p>생활 이야기를 나누고, 함께할 동료를 찾아보세요.</p></div><button className="comm-primary" onClick={() => session ? setEditor({}) : onLogin()}><Plus size={16} aria-hidden="true" />{kind === 'posts' ? '글쓰기' : '동행 모집'}</button></div>
    <SegmentedControl id="comm-community-type" label="커뮤니티 종류" value={kind} onChange={value => change(setKind, value)} options={[{ value: 'posts', label: '게시글' }, { value: 'companions', label: '동행 모집' }]} />
    <div id="comm-community-type-panel" role="tabpanel" aria-labelledby={`comm-community-type-${kind}`}>
    <div className="comm-community-filters"><FormSelect label="지역" value={region} onChange={event => change(setRegion, event.target.value)} options={regionOptions} disabled={regions.loading || !!regions.error} />
      {kind === 'posts' ? <FormSelect label="분류" value={category} onChange={event => change(setCategory, event.target.value)} options={[{ value: '', label: '전체 게시글' }, ...categories]} /> : <FormSelect label="모집 상태" value={status} onChange={event => change(setStatus, event.target.value)} options={[{ value: '', label: '전체 모집' }, { value: 'open', label: '모집 중' }, { value: 'closed', label: '마감' }]} />}
    </div>
    {regions.error && <p className="comm-error" role="alert">지역을 불러오지 못했어요. <button onClick={regions.retry}>다시 시도</button></p>}
    {kind === 'posts' && <form className="comm-search" onSubmit={event => { event.preventDefault(); change(setQuery, search.trim()) }}><input aria-label="게시글 검색" placeholder="궁금한 생활 정보를 검색해 보세요" value={search} onChange={event => setSearch(event.target.value)} /><button className="comm-secondary">검색</button></form>}
    {resource.loading ? <p className="comm-state" role="status">불러오는 중…</p> : resource.error ? <div className="comm-state" role="alert"><p>{resource.error.message}</p><button onClick={resource.retry}>다시 시도</button></div> : <>
      <p className="comm-community-count">전체 {resource.data?.count ?? items(resource.data).length}개</p>
      {items(resource.data).length ? <div className="comm-community-list">{items(resource.data).map(item => <button className="comm-community-card" key={item.id} onClick={() => setSelected(item.id)}>
        <div className="comm-community-meta"><span className="comm-tag">{kind === 'posts' ? categories.find(category => category.value === item.category)?.label : item.status === 'open' ? '모집 중' : '마감'}</span><span>{item.region_name || regionOptions.find(region => region.value === item.region)?.label || '충남 전체'}</span></div>
        <h3>{item.title}</h3><p>{kind === 'posts' ? item.preview : item.body || '함께할 동료를 찾고 있어요.'}</p>
        {kind === 'companions' && <p>{item.meet_place || '장소 협의'} · {dateLabel(item.meet_at)}</p>}
        <footer><span>{item.author?.name} · {new Date(item.created_at).toLocaleDateString('ko-KR')}</span><span className="comm-community-stats">{kind === 'posts' ? <><Heart size={14} fill={item.is_liked ? 'currentColor' : 'none'} aria-hidden="true" />{item.like_count}<MessageCircle size={14} aria-hidden="true" />{item.comment_count}</> : <><Users size={15} aria-hidden="true" />{item.participant_count} / {item.capacity}명{item.is_joined && ' · 참여 중'}</>}</span></footer>
      </button>)}</div> : <p className="comm-state">{region || (kind === 'posts' ? query || category : status) ? '조건에 맞는 글이 없어요.' : kind === 'posts' ? '아직 게시글이 없어요. 첫 이야기를 남겨보세요.' : '아직 동행 모집이 없어요. 함께할 동료를 모집해 보세요.'}</p>}
      <Pagination page={page} count={resource.data?.count || 0} onChange={setPage} />
    </>}
    </div>
    {selected && <CommunityDetail key={`${kind}-${selected}-${session ? 'member' : 'guest'}`} kind={kind} id={selected} session={session} onLogin={onLogin} onClose={() => { setSelected(null); resource.retry() }} onEdit={post => { setSelected(null); setEditor(post) }} />}
    {editor && <CommunityEditor kind={kind} initial={editor} regions={regionOptions} onClose={() => setEditor(null)} onSaved={post => { setEditor(null); setSelected(post.id); resource.retry() }} />}
  </section>
}
