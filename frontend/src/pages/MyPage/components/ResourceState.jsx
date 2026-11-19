import { Link } from 'react-router-dom'
export default function ResourceState({ resource, children }) {
  if (resource.loading) return <p className="my-state" role="status">정보를 불러오고 있어요.</p>
  if (resource.error) return <div className="my-state" role="alert"><p>{resource.error.status === 401 ? '로그인이 만료되었습니다.' : resource.error.message}</p>{resource.error.status === 401 ? <Link className="my-secondary" to="/login" state={{ from: '/mypage' }}>다시 로그인</Link> : <button className="my-secondary" onClick={resource.retry}>다시 시도</button>}</div>
  return children(resource.data)
}
