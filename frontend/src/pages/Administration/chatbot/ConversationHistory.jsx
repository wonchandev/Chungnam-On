import { useCallback, useState } from 'react'
import { ChevronRight, MessageCircle } from 'lucide-react'
import { adminRequest, rows } from '../api.js'
import useAdminResource from '../useAdminResource.js'
import ResourceState from '../components/ResourceState.jsx'

export default function ConversationHistory({ onSelect, loading }) {
  const [page, setPage] = useState(1)
  const load = useCallback(signal => adminRequest('assistant/conversations/', { signal, query: { page } }), [page])
  const resource = useAdminResource(load)
  return <div className="assistant-history"><h3>이전 대화</h3><p>궁금했던 이야기를 이어서 질문해 보세요.</p>
    <ResourceState resource={resource}>{data => <>
      {!rows(data).length && <p className="admin-state">아직 저장된 대화가 없어요.</p>}
      {rows(data).map(item => <button key={item.id} className="assistant-history-item" disabled={loading} onClick={() => onSelect(item.id)}><MessageCircle size={18} aria-hidden="true" /><span><strong>{item.title || '새 대화'}</strong><time>{new Date(item.updated_at).toLocaleDateString('ko-KR')}</time></span><ChevronRight size={16} aria-hidden="true" /></button>)}
      {data?.count > 20 && <div className="admin-pagination"><button disabled={page === 1 || loading} onClick={() => setPage(value => value - 1)}>이전</button><span>{page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next || loading} onClick={() => setPage(value => value + 1)}>다음</button></div>}
    </>}</ResourceState>
  </div>
}
