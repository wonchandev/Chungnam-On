import { useCallback } from 'react'
import { Star } from 'lucide-react'
import useAdminResource from '../../Administration/useAdminResource.js'
import ResourceState from './ResourceState.jsx'
import { myRequest } from '../api.js'

export default function Reputation({ userId }) {
  const load = useCallback(signal => myRequest(`users/${userId}/reputation/`, { signal }), [userId])
  const resource = useAdminResource(load)
  return <section className="my-card"><div className="my-section-heading"><h2><Star size={20} />나의 평판</h2><span>함께 일한 사람들의 평가</span></div><ResourceState resource={resource}>{data => <>
    <p className="my-section-description">받은 후기 {data.review_count}개 · 현재 온도 {Number(data.temperature).toFixed(1)}°</p>
    {!data.recent_reviews?.length ? <p className="my-state">아직 받은 후기가 없어요. 근무 완료 후 서로 평가할 수 있어요.</p> : <div className="my-reviews">{data.recent_reviews.map(review => <article key={review.id}><div><strong>{review.reviewer_name}</strong><span><Star size={13} />{review.score} / 5</span></div><p>{review.comment || '작성된 후기 내용이 없습니다.'}</p><time>{new Date(review.created_at).toLocaleDateString('ko-KR')}</time></article>)}</div>}
  </>}</ResourceState></section>
}
