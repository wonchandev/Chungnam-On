import { useEffect, useState } from 'react'

export default function useHomeResource(load) {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState({ data: null, error: null, loading: true })
  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then(
      (data) => { if (!controller.signal.aborted) setState({ data, error: null, loading: false }) },
      (error) => { if (!controller.signal.aborted) setState({ data: null, error, loading: false }) },
    )
    return () => controller.abort()
  }, [load, attempt])
  const retry = () => {
    setState({ data: null, error: null, loading: true })
    setAttempt((value) => value + 1)
  }
  return { ...state, retry }
}
