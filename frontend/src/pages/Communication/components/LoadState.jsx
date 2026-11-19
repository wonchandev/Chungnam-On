export default function LoadState({ resource, empty = '등록된 항목이 없어요.', children }) {
  if (resource.loading) return <p className="comm-state" role="status">불러오는 중…</p>
  if (resource.error) return <div className="comm-state" role="alert"><p>{resource.error.message}</p><button type="button" onClick={resource.retry}>다시 시도</button></div>
  if (!resource.data?.length) return <p className="comm-state">{empty}</p>
  return children(resource.data)
}
