import { useCallback, useState } from 'react'
import { ChevronRight, ClipboardList } from 'lucide-react'
import FormSelect from '../../../components/FormSelect.jsx'
import useAdminResource from '../useAdminResource.js'
import { adminRequest, complaintCategories, complaintStatuses, rows } from '../api.js'
import ResourceState from './ResourceState.jsx'

export default function ComplaintList({ preview = false, onOpen }) {
  const [filters, setFilters] = useState({ status: '', category: '', page: 1 })
  const load = useCallback(async signal => {
    if (!preview) return adminRequest('admin-info/complaints/', { signal, query: filters })
    const results = await Promise.all(['received', 'in_progress'].map(status => adminRequest('admin-info/complaints/', { signal, query: { status } })))
    return results.flatMap(rows).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 3)
  }, [preview, filters])
  const resource = useAdminResource(load)
  return <>
    {!preview && <div className="admin-complaint-filters"><FormSelect label="처리 상태" name="status" value={filters.status} options={complaintStatuses} onChange={event => setFilters(current => ({ ...current, status: event.target.value, page: 1 }))} /><FormSelect label="문의 분야" name="category" value={filters.category} options={[{ value: '', label: '전체 분야' }, ...complaintCategories]} onChange={event => setFilters(current => ({ ...current, category: event.target.value, page: 1 }))} /></div>}
    <ResourceState resource={resource}>{data => <>
      {!rows(data).length ? <p className="admin-state">{preview ? '진행 중인 문의가 없어요.' : '조건에 맞는 문의 내역이 없어요.'}</p> : <div className="admin-complaint-list">{rows(data).map(complaint => <button className="admin-service-row" key={complaint.id} onClick={() => onOpen(complaint.id)}>
        <span className="admin-row-icon"><ClipboardList size={22} aria-hidden="true" /></span><span className="admin-row-content"><strong>{complaint.title}</strong><span>{complaint.category_label} · {new Date(complaint.created_at).toLocaleDateString('ko-KR')}</span><small className={`admin-status is-${complaint.status}`}>{complaint.status_label}</small></span><ChevronRight size={18} aria-hidden="true" />
      </button>)}</div>}
      {!preview && data?.count > 20 && <div className="admin-pagination"><button disabled={filters.page === 1} onClick={() => setFilters(current => ({ ...current, page: current.page - 1 }))}>이전</button><span>{filters.page} / {Math.ceil(data.count / 20)}</span><button disabled={!data.next} onClick={() => setFilters(current => ({ ...current, page: current.page + 1 }))}>다음</button></div>}
    </>}</ResourceState>
  </>
}
