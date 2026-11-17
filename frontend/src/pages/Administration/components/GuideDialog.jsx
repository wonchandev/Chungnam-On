import { useCallback } from 'react'
import { ExternalLink } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import useAdminResource from '../useAdminResource.js'
import { adminRequest, sourceUrl } from '../api.js'
import ResourceState from './ResourceState.jsx'

export default function GuideDialog({ id, onClose }) {
  const load = useCallback(signal => adminRequest(`admin-info/guides/${id}/`, { signal }), [id])
  const resource = useAdminResource(load)
  return <HomeDialog title="행정 정보 안내" onClose={onClose} className="admin-dialog">
    <ResourceState resource={resource}>{guide => <article className="admin-guide-detail">
      <span className="admin-category-tag">{guide.category_label}</span><h3>{guide.title}</h3>
      {guide.summary && <p className="admin-guide-summary">{guide.summary}</p>}
      <p className="admin-guide-body">{guide.body}</p>
      <p className="admin-guide-updated">최근 수정: {new Date(guide.updated_at).toLocaleDateString('ko-KR')}</p>
      {sourceUrl(guide.source_url) && <a className="admin-primary" href={sourceUrl(guide.source_url)} target="_blank" rel="noopener noreferrer">공식 출처 확인<ExternalLink size={16} aria-hidden="true" /></a>}
      <p className="admin-footnote">일반 안내입니다. 실제 신청 조건과 절차는 공식 기관에서 확인해 주세요.</p>
    </article>}</ResourceState>
  </HomeDialog>
}
