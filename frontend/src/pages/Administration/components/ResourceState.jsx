export default function ResourceState({ resource, children }) {
  if (resource.loading) return <p className="admin-state" role="status">정보를 불러오고 있어요.</p>
  if (resource.error) return <div className="admin-state" role="alert"><p>{resource.error.status === 401 ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : resource.error.message}</p><button type="button" onClick={resource.retry}>다시 시도</button></div>
  return children(resource.data)
}
