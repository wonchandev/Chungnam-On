export const categories = [{ value: 'life', label: '생활정보' }, { value: 'review', label: '근무후기' }, { value: 'job_info', label: '일자리정보' }, { value: 'free', label: '자유' }]
export function dateLabel(value) { return value ? new Date(value).toLocaleString('ko-KR', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '일정 협의' }
