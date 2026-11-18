import { apiRequest } from '../../api/client.js'
import { getSession, saveSession } from '../../api/session.js'

export function myRequest(path, options = {}) {
  const session = getSession()
  return apiRequest(path, { accessToken: session?.access, refreshToken: session?.refresh, onRefresh: saveSession, ...options })
}
export function rows(data) { return Array.isArray(data) ? data : data?.results || [] }
export function errorText(error) { return error.status === 401 ? '로그인이 만료되었습니다. 다시 로그인해 주세요.' : error.message || '요청을 처리하지 못했습니다.' }
export function fieldErrors(error) { return error.detail && typeof error.detail === 'object' && !Array.isArray(error.detail) ? error.detail : {} }
export function fieldError(errors, name) { return errors[name] ? [].concat(errors[name]).join(' ') : '' }
