import { apiRequest } from '../../api/client.js'
import { getSession, saveSession } from '../../api/session.js'

export function adminRequest(path, options = {}) {
  const session = getSession()
  return apiRequest(path, { accessToken: session?.access, refreshToken: session?.refresh, onRefresh: saveSession, ...options })
}

export function rows(data) { return Array.isArray(data) ? data : data?.results || [] }
export function errorText(error) {
  if (error.status === 401) return '로그인이 만료되었습니다. 다시 로그인해 주세요.'
  return error.message || '정보를 불러오지 못했습니다. 다시 시도해 주세요.'
}
export function sourceUrl(value) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null }
  catch { return null }
}

export const guideCategories = [
  { value: '', label: '전체 분야' }, { value: 'visa', label: '비자·체류' },
  { value: 'labor', label: '근로·계약' }, { value: 'insurance', label: '건강보험' },
  { value: 'tax', label: '세금·연금' }, { value: 'life', label: '생활 정보' }, { value: 'etc', label: '기타' },
]
export const complaintCategories = [
  { value: 'visa', label: '비자·체류' }, { value: 'labor', label: '근로·계약' },
  { value: 'wage', label: '임금 체불·급여' }, { value: 'insurance', label: '건강보험·산재' },
  { value: 'life', label: '생활' }, { value: 'etc', label: '기타' },
]
export const complaintStatuses = [{ value: '', label: '전체 상태' }, { value: 'received', label: '접수' }, { value: 'in_progress', label: '처리중' }, { value: 'resolved', label: '답변 완료' }]
