import { apiRequest } from '../../api/client.js'
import { getSession, saveSession } from '../../api/session.js'

export function communicationRequest(path, options = {}) {
  const session = getSession()
  return apiRequest(path, { accessToken: session?.access, refreshToken: session?.refresh, onRefresh: saveSession, ...options })
}
export function socketUrl(path) {
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  const url = new URL(base, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = path
  url.search = ''
  url.searchParams.set('token', getSession()?.access || '')
  return url.href
}
export function items(data) { return Array.isArray(data) ? data : data?.results || [] }
export function errorMessage(error) {
  if (error.status === 401) return '로그인이 만료되었습니다. 다시 로그인해 주세요.'
  const detail = error.detail
  const messages = detail && typeof detail === 'object' ? Object.values(detail).flat().filter(value => typeof value === 'string') : []
  return messages.length ? messages.join(' ') : error.message
}
