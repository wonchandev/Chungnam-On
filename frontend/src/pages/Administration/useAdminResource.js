import { useCallback, useEffect, useState } from 'react'

export default function useAdminResource(load) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState({ load: null, attempt: -1, data: null, error: null })
  useEffect(() => {
    const controller = new AbortController()
    Promise.resolve().then(() => load(controller.signal)).then(
      data => { if (!controller.signal.aborted) setResult({ load, attempt, data, error: null }) },
      error => { if (!controller.signal.aborted) setResult({ load, attempt, data: null, error }) },
    )
    return () => controller.abort()
  }, [load, attempt])
  const retry = useCallback(() => setAttempt(value => value + 1), [])
  const loading = result.load !== load || result.attempt !== attempt
  return { data: loading ? null : result.data, error: loading ? null : result.error, loading, retry }
}
