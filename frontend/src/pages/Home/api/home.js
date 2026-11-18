import { apiGet, apiRequest } from '../../../api/client.js'

export const homeApi = {
  urgent: (options) => apiGet('jobs/urgent/', { ...options, query: { limit: 10 } }),
  popularCategories: (options) => apiGet('jobs/popular-categories/', { ...options, query: { limit: 4 } }),
  recommended: (options) => apiGet('jobs/recommended/', { ...options, query: { limit: 3 } }),
  ticker: (options) => apiGet('jobs/ticker/', options),
  regions: (options) => apiGet('regions/', { ...options, query: { level: 'sigungu' } }),
  jobs: (query, options) => apiGet('jobs/', { ...options, query }),
  detail: (id, options) => apiGet(`jobs/${id}/`, options),
  apply: (id, options) => apiRequest(`jobs/${id}/apply/`, { ...options, method: 'POST', body: {} }),
  openRoom: (jobId, options) => apiRequest('chat/rooms/', { ...options, method: 'POST', body: { job_id: jobId } }),
  companions: (jobId, options) => apiGet('community/companions/', { ...options, query: { job: jobId, status: 'open' } }),
  createCompanion: (body, options) => apiRequest('community/companions/', { ...options, method: 'POST', body }),
  joinCompanion: (id, joined, options) => apiRequest(`community/companions/${id}/join/`, { ...options, method: joined ? 'DELETE' : 'POST' }),
}
