import { useCallback, useState } from 'react'
import { Bell } from 'lucide-react'
import useAdminResource from '../useAdminResource.js'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import { adminRequest, errorText, rows } from '../api.js'
import ResourceState from './ResourceState.jsx'

function NotificationDialog({ onClose, onChange, onComplaint }) {
  const [page, setPage] = useState(1)
  const [unread, setUnread] = useState(false)
  const [readIds, setReadIds] = useState(new Set())
  const [allRead, setAllRead] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const load = useCallback(signal => adminRequest('notifications/', { signal, query: { page, unread: unread || undefined } }), [page, unread])
  const resource = useAdminResource(load)
  async function markRead(id) {
    if (busy) return
    setBusy(true); setError('')
    try {
      await adminRequest(id ? `notifications/${id}/read/` : 'notifications/read-all/', { method: 'POST' })
      if (id) setReadIds(current => new Set([...current, id]))
      else setAllRead(true)
      onChange()
      if (unread) resource.retry()
    } catch (failure) { setError(errorText(failure)) }
    finally { setBusy(false) }
  }
  return <HomeDialog title="알림" onClose={onClose} className="admin-dialog"><div className="admin-dialog-content">
    <div className="admin-notification-toolbar"><label><input type="checkbox" checked={unread} onChange={event => { setUnread(event.target.checked); setPage(1) }} /> 읽지 않은 알림만</label><button className="admin-text-button" disabled={busy} onClick={() => markRead()}>모두 읽음</button></div>
    {error && <p className="admin-error" role="alert">{error}</p>}
    <ResourceState resource={resource}>{data => <>
      {!rows(data).length && <p className="admin-state">새로운 알림이 없어요.</p>}
      <div className="admin-notifications">{rows(data).map(notification => {
        const isRead = notification.is_read || readIds.has(notification.id) || allRead
        return <article key={notification.id} className={isRead ? 'is-read' : ''}><div><h3>{notification.title}</h3>{!isRead && <span className="admin-new-dot" aria-label="읽지 않음" />}</div><p>{notification.body}</p><time>{new Date(notification.created_at).toLocaleString('ko-KR')}</time><div className="admin-notification-actions">{!isRead && <button className="admin-text-button" disabled={busy} onClick={() => markRead(notification.id)}>읽음 처리</button>}{notification.type === 'complaint' && Number.isInteger(notification.data?.complaint_id) && <button className="admin-text-button" onClick={() => onComplaint(notification.data.complaint_id)}>문의 답변 보기</button>}</div></article>
      })}</div>
      {data?.count > 20 && <div className="admin-pagination"><button disabled={page === 1} onClick={() => setPage(value => value - 1)}>이전</button><span>{page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next} onClick={() => setPage(value => value + 1)}>다음</button></div>}
    </>}</ResourceState>
  </div></HomeDialog>
}

function MemberNotifications({ onComplaint }) {
  const [open, setOpen] = useState(false)
  const load = useCallback(signal => adminRequest('notifications/unread-count/', { signal }), [])
  const unread = useAdminResource(load)
  const count = unread.data?.unread_count || 0
  return <><button className="admin-bell" aria-label={`알림${count ? ` ${count}개 읽지 않음` : ''}`} onClick={() => { setOpen(true); unread.retry() }}><Bell size={22} aria-hidden="true" />{count > 0 && <span>{count > 99 ? '99+' : count}</span>}</button>{open && <NotificationDialog onClose={() => { setOpen(false); unread.retry() }} onChange={unread.retry} onComplaint={id => { setOpen(false); onComplaint(id) }} />}</>
}
export default function Notifications({ session, onLogin, onComplaint }) {
  return session ? <MemberNotifications onComplaint={onComplaint} /> : <button className="admin-bell" aria-label="로그인하고 알림 확인" onClick={onLogin}><Bell size={22} aria-hidden="true" /></button>
}
