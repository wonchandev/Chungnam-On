import { useCallback, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import useAdminResource from '../../Administration/useAdminResource.js'
import ResourceState from './ResourceState.jsx'
import { myRequest, rows, errorText, fieldErrors, fieldError } from '../api.js'

const reasons = [{ value: 'spam', label: '스팸·광고' }, { value: 'abuse', label: '욕설·비하' }, { value: 'fraud', label: '사기·임금 체불 의심' }, { value: 'illegal', label: '불법·위험' }, { value: 'other', label: '기타' }]
function TargetPicker({ type, value, onChange }) {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState('')
  const load = useCallback(signal => myRequest(type === 'job' ? 'jobs/' : 'chat/rooms/', { signal, query: { page, ...(type === 'job' ? { q: search } : {}) } }), [type, page, search])
  const resource = useAdminResource(load)
  return <div className="my-target-picker">{type === 'job' && <div className="my-search"><input aria-label="신고할 공고 검색" placeholder="공고 제목으로 검색" value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); setSearch(draft.trim()); setPage(1); onChange('') } }} /><button type="button" aria-label="공고 검색" onClick={() => { setSearch(draft.trim()); setPage(1); onChange('') }}><Search size={18} /></button></div>}
    <ResourceState resource={resource}>{data => {
      const options = type === 'job' ? rows(data).map(job => ({ id: job.id, label: job.title, sub: job.company_name })) : type === 'room' ? rows(data).map(room => ({ id: room.id, label: `${room.counterpart?.name || '상대방'}님과의 대화`, sub: room.job?.title })) : [...new Map(rows(data).filter(room => room.counterpart).map(room => [room.counterpart.id, { id: room.counterpart.id, label: room.counterpart.name, sub: '대화 상대' }])).values()]
      return <>{!options.length && <p className="my-state">{type === 'job' ? '검색한 공고가 없어요.' : '선택할 대화가 없어요. 대화한 상대와 채팅방을 신고할 수 있어요.'}</p>}<div className="my-target-options">{options.map(option => <label key={option.id}><input type="radio" name="report-target" checked={String(option.id) === value} value={option.id} onChange={event => onChange(event.target.value)} /><span><strong>{option.label}</strong><small>{option.sub}</small></span></label>)}</div>{data?.count > 20 && <div className="my-pagination"><button type="button" disabled={page === 1} onClick={() => { setPage(current => current - 1); onChange('') }}>이전</button><span>{page} / {Math.ceil(data.count / 20)}</span><button type="button" disabled={!data.next} onClick={() => { setPage(current => current + 1); onChange('') }}>다음</button></div>}</>
    }}</ResourceState>
  </div>
}

export default function ReportDialog({ onClose, onSaved }) {
  const [type, setType] = useState('job')
  const [target, setTarget] = useState('')
  const [reason, setReason] = useState('other')
  const [detail, setDetail] = useState('')
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const pending = useRef(false)
  async function submit(event) {
    event.preventDefault()
    if (pending.current) return
    if (!target) { setErrors({ form: '신고할 대상을 선택해 주세요.' }); return }
    pending.current = true; setBusy(true); setErrors({})
    try { await myRequest('reports/', { method: 'POST', body: { target_type: type, target_id: Number(target), reason, detail: detail.trim() } }); onSaved() }
    catch (error) { setErrors({ ...fieldErrors(error), form: errorText(error) }) }
    finally { pending.current = false; setBusy(false) }
  }
  return <HomeDialog title="신고하기" onClose={onClose} className="my-dialog"><form className="my-form" onSubmit={submit}><fieldset disabled={busy}>
    <p className="my-help">문제가 있는 공고나 대화 상대를 선택해 운영자에게 알려주세요.</p>
    <FormSelect label="신고 대상" name="target_type" value={type} options={[{ value: 'job', label: '공고' }, { value: 'user', label: '대화 상대' }, { value: 'room', label: '채팅방' }]} onChange={event => { setType(event.target.value); setTarget(''); setErrors({}) }} />
    <TargetPicker key={type} type={type} value={target} onChange={setTarget} />
    <FormSelect label="신고 사유" name="reason" value={reason} options={reasons} onChange={event => setReason(event.target.value)} error={fieldError(errors, 'reason')} />
    <label className="my-field">상세 내용<textarea rows={4} maxLength={500} value={detail} onChange={event => setDetail(event.target.value)} placeholder="확인이 필요한 내용을 작성해 주세요." /><small>{detail.length} / 500자</small></label>
    {errors.detail && <p className="my-error">{fieldError(errors, 'detail')}</p>}{errors.form && <p className="my-error" role="alert">{errors.form}</p>}
    <button className="my-primary" disabled={!target || busy}>{busy ? '접수 중…' : '신고 접수'}</button>
  </fieldset></form></HomeDialog>
}
