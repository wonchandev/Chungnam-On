export default function CommunityPagination({ page, count, onChange }) {
  return count > 20 && <div className="comm-pagination"><button disabled={page <= 1} onClick={() => onChange(page - 1)}>이전</button><span>{page} / {Math.ceil(count / 20)}</span><button disabled={page * 20 >= count} onClick={() => onChange(page + 1)}>다음</button></div>
}
