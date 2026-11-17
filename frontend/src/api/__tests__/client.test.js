import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { apiGet, apiRequest, ApiError } from '../client.js'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } })

test('sends encoded search parameters, language and optional JWT', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/jobs/?q=%EC%95%84%EC%82%B0&region=44200&urgent=false')
    assert.equal(options.headers.Authorization, 'Bearer access')
    assert.equal(options.headers['Accept-Language'], 'vi')
    return json({ count: 0, results: [] })
  }
  assert.deepEqual(await apiGet('/jobs/', { baseUrl: '/api/', query: { q: '아산', region: '44200', urgent: false, unused: '' }, language: 'vi', accessToken: 'access' }), { count: 0, results: [] })
})

test('preserves backend errors for login and bookmark feedback', async () => {
  globalThis.fetch = async () => json({ code: 'not_authenticated', message: '로그인이 필요합니다.', detail: null }, 401)
  await assert.rejects(apiGet('jobs/'), (error) => error instanceof ApiError && error.status === 401 && error.code === 'not_authenticated' && error.message === '로그인이 필요합니다.')
})

test('rejects HTML responses instead of treating a proxy error as an empty list', async () => {
  globalThis.fetch = async () => new Response('<html>SPA fallback</html>', { headers: { 'content-type': 'text/html' } })
  await assert.rejects(apiGet('jobs/'), (error) => error.code === 'invalid_response')
})

test('DELETE without a response body succeeds', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/jobs/1/bookmark/')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  }
  assert.equal(await apiRequest('jobs/1/bookmark/', { method: 'DELETE' }), null)
})

test('refreshes an expired access token and persists the rotated refresh token', async () => {
  const calls = []
  let saved
  globalThis.fetch = async (url, options) => {
    calls.push(url)
    if (url.endsWith('auth/refresh/')) {
      assert.deepEqual(JSON.parse(options.body), { refresh: 'old-refresh' })
      return json({ access: 'new-access', refresh: 'new-refresh' })
    }
    return options.headers.Authorization === 'Bearer new-access' ? json([{ id: 1 }]) : json({ code: 'token_not_valid' }, 401)
  }
  assert.deepEqual(await apiGet('jobs/recommended/', { accessToken: 'old-access', refreshToken: 'old-refresh', onRefresh: (tokens) => { saved = tokens } }), [{ id: 1 }])
  assert.deepEqual(saved, { access: 'new-access', refresh: 'new-refresh' })
  assert.equal(calls.length, 3)
})

test('propagates cancellation when navigating away', async () => {
  const controller = new AbortController()
  controller.abort()
  globalThis.fetch = async (url, options) => { options.signal.throwIfAborted() }
  await assert.rejects(apiGet('jobs/', { signal: controller.signal }), { name: 'AbortError' })
})

test('uploads multipart media without overriding its boundary and preserves it on token refresh', async () => {
  const body = new FormData()
  body.set('image', new Blob(['image-data'], { type: 'image/png' }), 'photo.png')
  body.set('target', 'vi')
  let uploads = 0
  globalThis.fetch = async (url, options) => {
    if (url.endsWith('auth/refresh/')) return json({ access: 'fresh' })
    uploads++
    assert.equal(options.body, body)
    assert.equal(options.headers['Content-Type'], undefined)
    return uploads === 1 ? json({ message: 'expired' }, 401) : json({ translated_text: 'result' })
  }
  assert.deepEqual(await apiRequest('translate/image/', { method: 'POST', body, accessToken: 'expired', refreshToken: 'refresh' }), { translated_text: 'result' })
  assert.equal(uploads, 2)
})

test('returns TTS audio after token refresh while keeping JSON provider errors readable', async () => {
  globalThis.fetch = async (url, options) => {
    if (url.endsWith('auth/refresh/')) return json({ access: 'fresh' })
    return options.headers.Authorization === 'Bearer fresh' ? new Response('mp3-bytes', { headers: { 'content-type': 'audio/mpeg' } }) : json({ message: 'expired' }, 401)
  }
  const result = await apiRequest('translate/tts/', { method: 'POST', body: { text: 'hello', language: 'en' }, responseType: 'blob', accessToken: 'old', refreshToken: 'refresh' })
  assert.equal(result.type, 'audio/mpeg')
  assert.equal(await result.text(), 'mp3-bytes')
  globalThis.fetch = async () => json({ code: 'tts_unavailable', message: '음성 서비스를 사용할 수 없습니다.' }, 503)
  await assert.rejects(apiRequest('translate/tts/', { responseType: 'blob' }), error => error.code === 'tts_unavailable')
})
