import { useCallback, useState } from 'react'
import useResource from '../../Administration/useAdminResource.js'
import { communicationRequest, errorMessage, items } from '../api.js'
import { dateLabel } from './communityHelpers.js'
import Pagination from './CommunityPagination.jsx'

export default function CommunityComments({ id, session, onLogin }) {
  const [page, setPage] = useState(1)
  const load = useCallback(signal => communicationRequest(`community/posts/${id}/comments/`, { signal, query: { page } }), [id, page])
  const resource = useResource(load)
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function mutate(event, commentId) {
    event.preventDefault()
    if (!session) { onLogin(); return }
    if (busy || (!commentId && !body.trim())) return
    if (commentId && !window.confirm('댓글을 삭제할까요?')) return
    setBusy(true); setError('')
    try {
      await communicationRequest(commentId ? `community/comments/${commentId}/` : `community/posts/${id}/comments/`, { method: commentId ? 'DELETE' : 'POST', ...(!commentId && { body: { body: body.trim() } }) })
      if (!commentId) setBody('')
      if (commentId && items(resource.data).length === 1 && page > 1) setPage(value => value - 1)
      else resource.retry()
    } catch (error) { setError(errorMessage(error)) }
    finally { setBusy(false) }
  }
  return <section className="comm-comments"><h4>댓글 {resource.data?.count ?? ''}</h4>
    {resource.loading ? <p role="status">불러오는 중…</p> : resource.error ? <div className="comm-error" role="alert"><p>{resource.error.message}</p><button onClick={resource.retry}>다시 시도</button></div> : <><div className="comm-comment-list">{items(resource.data).map(comment => <article key={comment.id}><div><strong>{comment.author?.name}</strong><time>{dateLabel(comment.created_at)}</time>{comment.is_mine && <button disabled={busy} onClick={event => mutate(event, comment.id)}>삭제</button>}</div><p>{comment.body}</p>{comment.original_body !== comment.body && <details><summary>원문 보기</summary><p>{comment.original_body}</p></details>}</article>)}</div>{!items(resource.data).length && <p className="comm-community-note">첫 댓글을 남겨보세요.</p>}<Pagination page={page} count={resource.data?.count || 0} onChange={setPage} /></>}
    {session ? <form className="comm-dialog-content" onSubmit={mutate}><label className="comm-input-label">댓글 작성<textarea required maxLength={1000} value={body} onChange={event => setBody(event.target.value)} disabled={busy} rows={3} /></label><button className="comm-primary" disabled={busy || !body.trim()}>{busy ? '처리 중…' : '댓글 등록'}</button></form> : <button className="comm-secondary" onClick={onLogin}>로그인하고 댓글 남기기</button>}
    {error && <p className="comm-error" role="alert">{error}</p>}
  </section>
}
