import { rows } from '../utils/formatters.js'

export default function ResourceState({ resource, empty, children, onLogin }) {
  if (resource.loading) return <div className="home-state home-loading" role="status">일자리를 불러오고 있어요<span aria-hidden="true">···</span></div>
  if (resource.error) return <div className="home-state" role="alert"><p>{resource.error.status === 401 ? '로그인이 만료됐어요.' : '일자리를 불러오지 못했어요.'}</p><button type="button" onClick={resource.error.status === 401 ? onLogin : resource.retry}>{resource.error.status === 401 ? '다시 로그인' : '다시 시도'}</button></div>
  if (!rows(resource.data).length) return <div className="home-state"><p>{empty}</p></div>
  return children(rows(resource.data))
}
