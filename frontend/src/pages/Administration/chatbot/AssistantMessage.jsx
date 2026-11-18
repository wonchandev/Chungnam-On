import { useState } from 'react'
import { BookOpen, Bot, ChevronRight, ThumbsDown, ThumbsUp } from 'lucide-react'
import { adminRequest, errorText, sourceUrl } from '../api.js'

export default function AssistantMessage({ message, onGuide, onFeedback }) {
  const [rating, setRating] = useState(message.feedback || '')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  async function feedback(next) {
    if (busy || rating === next) return
    setBusy(true); setNotice('')
    try {
      const result = await adminRequest(`assistant/messages/${message.id}/feedback/`, { method: 'POST', body: { rating: next } })
      setRating(result.feedback); onFeedback(message.id, result.feedback); setNotice('의견을 전달했어요.')
    } catch (failure) { setNotice(errorText(failure)) }
    finally { setBusy(false) }
  }
  const mine = message.role === 'user'
  return <article className={`assistant-message${mine ? ' is-user' : ''}${message.failed ? ' is-failed' : ''}`} aria-label={mine ? '내 질문' : 'AI 답변'}>
    {!mine && <span className="assistant-message-avatar" aria-hidden="true"><Bot size={17} /></span>}
    <div className="assistant-message-content"><div className="assistant-message-bubble"><p>{message.text}</p></div>
      {message.failed && <span className="assistant-failed-note">답변 수신을 확인하지 못했어요.</span>}
      {!mine && !!message.sources?.length && <div className="assistant-sources"><span><BookOpen size={13} aria-hidden="true" /> 참고한 행정 안내</span>{message.sources.map((source, index) => Number.isInteger(source.id) ? <button type="button" key={`${source.id}-${index}`} onClick={() => onGuide(source.id)}>{source.title}<ChevronRight size={14} aria-hidden="true" /></button> : sourceUrl(source.url) ? <a key={index} href={sourceUrl(source.url)} target="_blank" rel="noopener noreferrer">{source.title}</a> : null)}</div>}
      {!mine && Number.isInteger(message.id) && <div className="assistant-feedback"><button type="button" aria-label="도움이 되었어요" aria-pressed={rating === 'up'} disabled={busy} onClick={() => feedback('up')}><ThumbsUp size={14} /></button><button type="button" aria-label="아쉬워요" aria-pressed={rating === 'down'} disabled={busy} onClick={() => feedback('down')}><ThumbsDown size={14} /></button><span role="status">{notice}</span></div>}
    </div>
  </article>
}
