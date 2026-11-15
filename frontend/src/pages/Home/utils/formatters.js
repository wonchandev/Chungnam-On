export const money = (value) => new Intl.NumberFormat('ko-KR').format(value)
export const payLabel = (value) => value === 'hourly' ? '시급' : '일급'
export const rows = (value) => Array.isArray(value) ? value : value?.results || []
export const deadlineLabel = (job) => {
  const remaining = job.deadline ? new Date(`${job.deadline}T23:59:59+09:00`).getTime() - Date.now() : Infinity
  return remaining <= 3 * 24 * 60 * 60 * 1000 ? '마감임박' : '긴급채용'
}
