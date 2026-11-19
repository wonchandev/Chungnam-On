import { useCallback, useState } from 'react'
import { Building2, UserRound } from 'lucide-react'
import useHomeResource from '../../Home/hooks/useHomeResource.js'
import { communicationRequest, items } from '../api.js'
import LoadState from './LoadState.jsx'
import ChatDialog from './ChatDialog.jsx'

export default function RecentChats({ languages }) {
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState(null)
  const [count, setCount] = useState(0)
  const load = useCallback(async signal => {
    const data = await communicationRequest('chat/rooms/', { signal, query: { page } })
    if (!signal.aborted) setCount(data.count ?? items(data).length)
    return items(data)
  }, [page])
  const rooms = useHomeResource(load)
  return <>
    <div className="comm-section-heading"><h2>최근 대화</h2><span>전체 {count}개</span></div>
    <LoadState resource={rooms} empty="아직 대화가 없어요. 일자리 공고에서 문의를 시작해 보세요.">{data => <div className="comm-rooms">{data.map(room => <button className="comm-room" key={room.id} onClick={() => setSelected(room)}>
      <span className="comm-avatar">{room.counterpart?.profile_image ? <img src={room.counterpart.profile_image} alt="" /> : room.counterpart?.is_employer ? <Building2 size={23} /> : <UserRound size={23} />}</span>
      <span className="comm-room-text"><strong>{room.counterpart?.name || '대화 상대'}</strong><span>{room.last_message?.text || (room.last_message?.image ? '사진을 보냈습니다.' : '대화를 시작해 보세요.')}</span></span>
      <span className="comm-room-end"><time>{room.last_message_at ? new Date(room.last_message_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }) : ''}</time>{room.unread_count > 0 && <span className="comm-unread" aria-label={`읽지 않은 메시지 ${room.unread_count}개`}>{room.unread_count > 99 ? '99+' : room.unread_count}</span>}</span>
    </button>)}</div>}</LoadState>
    {count > 20 && <div className="comm-pagination"><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>이전</button><span>{page} / {Math.ceil(count / 20)}</span><button disabled={page * 20 >= count} onClick={() => setPage(value => value + 1)}>다음</button></div>}
    {selected && <ChatDialog initialRoom={selected} languages={languages} onClose={() => { setSelected(null); rooms.retry() }} />}
  </>
}
