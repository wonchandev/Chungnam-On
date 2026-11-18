import { useCallback, useState } from 'react'
import { Flag, ShieldCheck, UserRoundX } from 'lucide-react'
import FormSelect from '../../../components/FormSelect.jsx'
import useAdminResource from '../../Administration/useAdminResource.js'
import { myRequest, rows, errorText } from '../api.js'
import ResourceState from './ResourceState.jsx'
import ReportDialog from './ReportDialog.jsx'

function ReportHistory({ revision }) {
  const [page, setPage] = useState(1)
  const load = useCallback(signal => { void revision; return myRequest('reports/', { signal, query: { page } }) }, [page, revision])
  const resource = useAdminResource(load)
  return <ResourceState resource={resource}>{data => <>
    {!rows(data).length ? <p className="my-state">접수한 신고가 없어요.</p> : <div className="my-reports">{rows(data).map(report => <article key={report.id}><div><strong>{report.target_type_label || '대상'} 신고 · {report.reason_label || report.reason}</strong><span className={`my-status is-${report.status}`}>{report.status_label || report.status}</span></div>{report.detail && <p>{report.detail}</p>}<time>{new Date(report.created_at).toLocaleString('ko-KR')}</time></article>)}</div>}
    {data?.count > 20 && <div className="my-pagination"><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>이전</button><span>{page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next} onClick={() => setPage(value => value + 1)}>다음</button></div>}
  </>}</ResourceState>
}
function BlockedUsers() {
  const [page, setPage] = useState(1)
  const [roomPage, setRoomPage] = useState(1)
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const loadBlocks = useCallback(signal => myRequest('blocks/', { signal, query: { page } }), [page])
  const loadRooms = useCallback(signal => myRequest('chat/rooms/', { signal, query: { page: roomPage } }), [roomPage])
  const blocks = useAdminResource(loadBlocks)
  const rooms = useAdminResource(loadRooms)
  async function changeBlock(id, remove = false) {
    if (busy) return
    if (!window.confirm(remove ? '이 사용자의 차단을 해제할까요?' : '이 사용자를 차단할까요? 서로 채팅할 수 없게 됩니다.')) return
    setBusy(true); setNotice(''); setError('')
    try {
      await myRequest(`blocks/${id}/`, { method: remove ? 'DELETE' : 'POST' })
      if (remove && rows(blocks.data).length === 1 && page > 1) setPage(value => value - 1)
      else blocks.retry()
      setSelected(''); setNotice(remove ? '차단을 해제했어요.' : '사용자를 차단했어요.')
    } catch (failure) { setError(errorText(failure)) }
    finally { setBusy(false) }
  }
  const candidates = [...new Map(rows(rooms.data).filter(room => room.counterpart).map(room => [room.counterpart.id, room.counterpart])).values()]
  return <section className="my-card"><div className="my-section-heading"><h2><UserRoundX size={20} />차단 관리</h2><span>내가 차단한 사용자</span></div><p className="my-section-description">차단한 사용자와는 채팅할 수 없어요. 차단은 언제든 해제할 수 있습니다.</p>
    <ResourceState resource={blocks}>{data => <>
      {!rows(data).length ? <p className="my-state">차단한 사용자가 없어요.</p> : <div className="my-block-list">{rows(data).map(block => <div key={block.blocked}><span className="my-block-avatar"><UserRoundX size={20} /></span><span><strong>{block.blocked_name}</strong><small>{new Date(block.created_at).toLocaleDateString('ko-KR')} 차단</small></span><button className="my-secondary" disabled={busy} onClick={() => changeBlock(block.blocked, true)}>차단 해제</button></div>)}</div>}
      {data?.count > 20 && <div className="my-pagination"><button disabled={page === 1 || busy} onClick={() => setPage(value => value - 1)}>이전</button><span>{page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next || busy} onClick={() => setPage(value => value + 1)}>다음</button></div>}
    </>}</ResourceState>
    <div className="my-block-add"><h3>대화 상대 차단</h3><ResourceState resource={rooms}>{data => candidates.length ? <><FormSelect label="차단할 사용자" name="blocked_user" value={selected} disabled={busy} onChange={event => setSelected(event.target.value)} options={[{ value: '', label: '대화 상대 선택' }, ...candidates.map(user => ({ value: String(user.id), label: user.name }))]} /><button className="my-secondary" disabled={!selected || busy} onClick={() => changeBlock(Number(selected))}>선택한 사용자 차단</button>{data?.count > 20 && <div className="my-pagination"><button disabled={roomPage === 1} onClick={() => { setRoomPage(value => value - 1); setSelected('') }}>이전 대화</button><button disabled={!data.next} onClick={() => { setRoomPage(value => value + 1); setSelected('') }}>다음 대화</button></div>}</> : <p className="my-help">아직 대화한 상대가 없어요. 대화가 생기면 이곳에서 차단할 수 있어요.</p>}</ResourceState></div>
    {notice && <p className="my-success" role="status">{notice}</p>}{error && <p className="my-error" role="alert">{error}</p>}
  </section>
}
export default function SafetyPanel() {
  const [reportOpen, setReportOpen] = useState(false)
  const [revision, setRevision] = useState(0)
  const [notice, setNotice] = useState('')
  return <><section className="my-card"><div className="my-section-heading"><h2><Flag size={20} />신고 내역</h2><button className="my-secondary" onClick={() => setReportOpen(true)}>신고하기</button></div><p className="my-section-description">접수한 신고와 운영자의 처리 상태를 확인하세요.</p>{notice && <p className="my-success" role="status">{notice}</p>}<ReportHistory revision={revision} /></section><BlockedUsers /><p className="my-safety-note"><ShieldCheck size={17} />신고와 차단은 별도로 처리됩니다. 신고만으로 자동 차단되지는 않습니다.</p>{reportOpen && <ReportDialog onClose={() => setReportOpen(false)} onSaved={() => { setReportOpen(false); setRevision(value => value + 1); setNotice('신고를 접수했어요. 운영자가 확인합니다.') }} />}</>
}
