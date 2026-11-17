import { useEffect, useRef, useState } from 'react'
import { adminRequest, errorText } from '../api.js'

export default function useAssistantChat() {
  const [conversation, setConversation] = useState(null)
  const [messages, setMessages] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [masked, setMasked] = useState(false)
  const [historyVersion, setHistoryVersion] = useState(0)
  const request = useRef(null)
  const sequence = useRef(0)
  useEffect(() => () => request.current?.abort(), [])

  async function send(value = draft) {
    const text = value.trim()
    if (!text || text.length > 2000 || request.current) return
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setError(''); setMasked(false); setSuggestions([])
    const localId = `question-${++sequence.current}`
    setMessages(current => [...current, { id: localId, role: 'user', text, created_at: new Date().toISOString() }])
    setDraft('')
    try {
      const body = { message: text, stream: false }
      if (conversation?.id) body.conversation_id = conversation.id
      const result = await adminRequest('assistant/chat/', { method: 'POST', body, signal: controller.signal })
      if (controller.signal.aborted) return
      setConversation({ id: result.conversation_id, title: result.title || conversation?.title || text.slice(0, 50) })
      setMessages(current => [...current, { id: result.message_id, role: 'assistant', text: result.answer, sources: result.sources || [], created_at: new Date().toISOString() }])
      setSuggestions(result.suggestions || [])
      setMasked(!!result.pii_masked)
      if (result.pii_masked) setMessages(current => current.map(message => message.id === localId ? { ...message, text: '개인정보가 포함된 질문은 보호를 위해 표시하지 않습니다.' } : message))
      setHistoryVersion(version => version + 1)
    } catch (failure) {
      if (controller.signal.aborted) return
      setMessages(current => current.map(message => message.id === localId ? { ...message, failed: true } : message))
      setError(failure.status === 429 ? failure.message : `${errorText(failure)} 이전 대화에서 답변 여부를 확인한 후 다시 질문해 주세요.`)
      setHistoryVersion(version => version + 1)
    } finally {
      if (!controller.signal.aborted) { setBusy(false); request.current = null }
    }
  }
  async function openConversation(id) {
    if (request.current) return false
    const controller = new AbortController()
    request.current = controller
    setLoading(true); setError('')
    try {
      const data = await adminRequest(`assistant/conversations/${id}/`, { signal: controller.signal })
      if (controller.signal.aborted) return false
      setConversation({ id: data.id, title: data.title }); setMessages(data.turns || []); setSuggestions([]); setDraft(''); setMasked(false)
      return true
    } catch (failure) { if (!controller.signal.aborted) setError(errorText(failure)); return false }
    finally { if (!controller.signal.aborted) { setLoading(false); request.current = null } }
  }
  function newConversation() {
    if (request.current) return
    setConversation(null); setMessages([]); setSuggestions([]); setDraft(''); setError(''); setMasked(false)
  }
  function updateFeedback(id, feedback) { setMessages(current => current.map(message => message.id === id ? { ...message, feedback } : message)) }
  return { conversation, messages, suggestions, draft, setDraft, busy, loading, error, masked, historyVersion, send, openConversation, newConversation, updateFeedback }
}
