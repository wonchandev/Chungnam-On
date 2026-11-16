import { apiGet } from '../../../api/client.js'

export const homeApi = {
  urgent: (options) => apiGet('jobs/urgent/', { ...options, query: { limit: 10 } }),
  popularCategories: (options) => apiGet('jobs/popular-categories/', { ...options, query: { limit: 4 } }),
  recommended: (options) => apiGet('jobs/recommended/', { ...options, query: { limit: 3 } }),
  ticker: (options) => apiGet('jobs/ticker/', options),
  regions: (options) => apiGet('regions/', { ...options, query: { level: 'sigungu' } }),
  jobs: (query, options) => apiGet('jobs/', { ...options, query }),
  detail: (id, options) => apiGet(`jobs/${id}/`, options),
}
