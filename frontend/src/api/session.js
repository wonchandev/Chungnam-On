const key = 'chungnam-home-session'
const listeners = new Set()
export function readSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem(key) || 'null')
    return session?.access && session?.refresh ? session : null
  } catch { return null }
}
let current = readSession()
export const getSession = () => current
export function subscribeSession(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
export function saveSession(tokens) {
  if (tokens) sessionStorage.setItem(key, JSON.stringify(tokens))
  else sessionStorage.removeItem(key)
  current = tokens
  listeners.forEach(listener => listener())
}
