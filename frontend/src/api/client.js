const configuredBase = import.meta.env?.VITE_API_BASE_URL || '/api'

export class ApiError extends Error {
  constructor(message, status, code, detail) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.detail = detail
  }
}

// accessToken is supplied by the shared login flow; public home requests also
// work without it. Keep credentials and external-service keys on the backend.
export async function apiRequest(path, { signal, language = 'ko', accessToken, refreshToken, onRefresh, query = {}, baseUrl = configuredBase, method = 'GET', body, responseType = 'json' } = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const suffix = params.size ? `?${params}` : ''
  const headers = { Accept: 'application/json', 'Accept-Language': language }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  const multipart = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}${suffix}`, {
    headers,
    signal,
    method,
    body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  })
  if (response.status === 401 && refreshToken) {
    const tokens = await apiRequest('auth/refresh/', { method: 'POST', body: { refresh: refreshToken }, baseUrl, signal })
    const next = { access: tokens.access, refresh: tokens.refresh || refreshToken }
    try {
      return await apiRequest(path, { signal, language, accessToken: next.access, query, baseUrl, method, body, responseType })
    } finally {
      onRefresh?.(next)
    }
  }
  if (response.status === 204) return null
  if (response.ok && responseType === 'blob') return response.blob()
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await response.json() : null
  if (!response.ok) {
    throw new ApiError(data?.message || '정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', response.status, data?.code, data?.detail)
  }
  if (!isJson) throw new ApiError('서버 응답을 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.', response.status, 'invalid_response')
  return data
}

export const apiGet = (path, options) => apiRequest(path, options)
