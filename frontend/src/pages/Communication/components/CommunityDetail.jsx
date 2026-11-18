import { useCallback, useState } from 'react'
import { Heart } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import useResource from '../../Administration/useAdminResource.js'
import { communicationRequest, errorMessage, items } from '../api.js'
import { categories, dateLabel } from './communityHelpers.js'
import CommunityComments from './CommunityComments.jsx'
import Pagination from './CommunityPagination.jsx'

export default function CommunityDetail({ kind, id, session, onLogin, onClose, onEdit }) {
  const companion = kind === 'companions'
  const load = useCallback(signal => communicationRequest(`community/${kind}/${id}/`, { signal }), [kind, id])
  const resource = useResource(load)
  const [updated, setUpdated] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [original, setOriginal] = useState(false)
  const post = updated || resource.data
  async function action(name, method) {
    if (!session) { onLogin(); return }
    if (busy) return
    if (name === 'delete' && !window.confirm(companion ? '동행 모집을 삭제할까요?' : '게시글을 삭제할까요?')) return
    setBusy(true); setError('')
    try {
      const result = await communicationRequest(`community/${kind}/${id}/${name === 'delete' ? '' : `${name}/`}`, { method })
      if (name === 'delete') { onClose(); return }
      if (companion) setUpdated(result)
      else setUpdated(current => { const value = current || post; return { ...value, is_liked: !value.is_liked, like_count: value.like_count + (value.is_liked ? -1 : 1) } })
    } catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }
  return <HomeDialog title={companion ? '동행 모집' : '커뮤니티 이야기'} onClose={() => { if (!busy) onClose() }} className="comm-community-dialog">
    {resource.loading ? <p className="comm-state" role="status">불러오는 중…</p> : resource.error ? <div className="comm-state" role="alert"><p>{resource.error.message}</p><button onClick={resource.retry}>다시 시도</button></div> : post && <div className="comm-dialog-content">
      <div className="comm-community-meta"><span className="comm-tag">{companion ? post.status === 'open' ? '모집 중' : '마감' : categories.find(item => item.value === post.category)?.label}</span><span>{post.region_name}</span></div>
      <h3 className="comm-community-title">{original ? post.original_title : post.title}</h3><p className="comm-community-note">{post.author?.name} · {dateLabel(post.created_at)}</p>
      {!companion && (post.original_title !== post.title || post.original_body !== post.body) && <button className="comm-secondary" aria-pressed={original} onClick={() => setOriginal(value => !value)}>{original ? '번역 보기' : '원문 보기'}</button>}
      {post.image && <img className="comm-community-image" src={post.image} alt="게시글 첨부 사진" />}
      <p className="comm-community-body">{original ? post.original_body : post.body}</p>
      {companion && <><dl className="comm-companion-info"><div><dt>만날 장소</dt><dd>{post.meet_place || '협의 후 결정'}</dd></div><div><dt>만날 일시</dt><dd>{dateLabel(post.meet_at)}</dd></div><div><dt>모집 인원</dt><dd>{post.participant_count} / {post.capacity}명 (작성자 제외)</dd></div>{post.job_title && <div><dt>관련 공고</dt><dd>{post.job_title}</dd></div>}</dl>
        {!post.is_mine && <button className={post.is_joined ? 'comm-secondary' : 'comm-primary'} disabled={busy || (!post.is_joined && post.status !== 'open')} onClick={() => action('join', post.is_joined ? 'DELETE' : 'POST')}>{busy ? '처리 중…' : post.is_joined ? '참여 취소' : post.status === 'open' ? '동행 참여하기' : '모집이 마감됐어요'}</button>}
        {(post.is_mine || post.is_joined) && <Participants key={post.participant_count} id={id} />}
      </>}
      {!companion && <button className="comm-secondary comm-like" aria-pressed={post.is_liked} disabled={busy} onClick={() => action('like', post.is_liked ? 'DELETE' : 'POST')}><Heart size={18} fill={post.is_liked ? 'currentColor' : 'none'} aria-hidden="true" />좋아요 {post.like_count}</button>}
      {post.is_mine && <div className="comm-community-actions">{!companion && <button className="comm-secondary" disabled={busy} onClick={() => onEdit(post)}>수정</button>}<button className="comm-danger" disabled={busy} onClick={() => action('delete', 'DELETE')}>삭제</button></div>}
      {error && <p className="comm-error" role="alert">{error}</p>}
      {!companion && <CommunityComments id={id} session={session} onLogin={onLogin} />}
    </div>}
  </HomeDialog>
}

function Participants({ id }) {
  const [page, setPage] = useState(1)
  const load = useCallback(signal => communicationRequest(`community/companions/${id}/participants/`, { signal, query: { page } }), [id, page])
  const resource = useResource(load)
  return <section><h4>함께하는 동료</h4>{resource.loading ? <p role="status">불러오는 중…</p> : resource.error ? <div className="comm-error" role="alert"><p>{resource.error.message}</p><button onClick={resource.retry}>다시 시도</button></div> : <><p className="comm-community-note">전체 {resource.data?.count ?? items(resource.data).length}명</p>{items(resource.data).length ? <ul className="comm-participants">{items(resource.data).map(item => <li key={item.user.id}>{item.user.name}<span>{item.user.nationality}</span></li>)}</ul> : <p className="comm-state">아직 참여한 동료가 없어요.</p>}<Pagination page={page} count={resource.data?.count || 0} onChange={setPage} /></>}</section>
}
