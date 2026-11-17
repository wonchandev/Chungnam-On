import { useEffect, useRef, useState } from 'react'
import { Building2, ImagePlus, Menu, Phone, Send, UserRound } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import FormSelect from '../../../components/FormSelect.jsx'
import useHomeSession from '../../Home/hooks/useHomeSession.js'
import { communicationRequest, errorMessage, items, socketUrl } from '../api.js'

function mergeMessages(current, incoming) {
  return [...new Map([...current, ...incoming].map(message => [message.id, message])).values()].sort((a, b) => a.id - b.id)
}
export default function ChatDialog({ initialRoom, languages, onClose }) {
  const { session } = useHomeSession()
  const [room, setRoom] = useState(initialRoom)
  const [messages, setMessages] = useState([])
  const [user, setUser] = useState(null)
  const [text, setText] = useState('')
  const [image, setImage] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [paging, setPaging] = useState(false)
  const [cursor, setCursor] = useState(null)
  const [translated, setTranslated] = useState(true)
  const [settings, setSettings] = useState(false)
  const [replies, setReplies] = useState([])
  const [connected, setConnected] = useState(false)
  const [phone, setPhone] = useState('')
  const [retry, setRetry] = useState(0)
  const [changing, setChanging] = useState(false)
  const bottom = useRef(null)
  const fileInput = useRef(null)
  const socket = useRef(null)
  const path = `chat/rooms/${room.id}/`
  useEffect(() => {
    const controller = new AbortController()
    let alive = true
    Promise.all([communicationRequest('auth/me/', { signal: controller.signal }), communicationRequest(`${path}messages/`, { signal: controller.signal }), communicationRequest(path, { signal: controller.signal })])
      .then(([me, history, detail]) => {
        if (!alive) return
        setUser(me); setRoom(detail); setMessages(current => mergeMessages(items(history), current)); setCursor(history.next ? new URL(history.next, window.location.origin).searchParams.get('cursor') : null); setLoading(false)
        communicationRequest(`${path}read/`, { method: 'POST' }).catch(() => {})
      }).catch(failure => { if (alive) { setError(errorMessage(failure)); setLoading(false) } })
    communicationRequest('chat/quick-replies/', { signal: controller.signal }).then(data => { if (alive) setReplies(data) }).catch(() => {})
    return () => { alive = false; controller.abort() }
  }, [path, retry])
  useEffect(() => {
    const ws = new WebSocket(socketUrl(`/ws/chat/${room.id}/`))
    socket.current = ws
    let alive = true
    ws.onopen = () => { if (alive) setConnected(true) }
    ws.onclose = () => { if (alive) setConnected(false) }
    ws.onerror = () => { if (alive) setConnected(false) }
    ws.onmessage = event => {
      if (!alive) return
      let payload
      try { payload = JSON.parse(event.data) } catch { return }
      if (payload.type === 'message') {
        setMessages(current => mergeMessages(current, [payload.message]))
        communicationRequest(`${path}read/`, { method: 'POST' }).catch(() => {})
      }
      if (payload.type === 'presence') setRoom(current => current.counterpart?.id === payload.user ? { ...current, counterpart: { ...current.counterpart, is_online: payload.online } } : current)
      if (payload.type === 'error') setError(payload.message)
    }
    return () => { alive = false; ws.close() }
  }, [room.id, path, session?.access])
  useEffect(() => {
    if (connected) return
    const controller = new AbortController()
    const timer = setInterval(() => {
      if (document.visibilityState !== 'visible') return
      communicationRequest(`${path}messages/`, { signal: controller.signal }).then(data => {
        setMessages(current => mergeMessages(current, items(data)))
        communicationRequest(`${path}read/`, { method: 'POST' }).catch(() => {})
      }).catch(() => {})
    }, 8000)
    return () => { clearInterval(timer); controller.abort() }
  }, [connected, path])
  const lastId = messages.at(-1)?.id
  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest' }) }, [lastId])
  async function send(event) {
    event.preventDefault()
    if (busy || (!text.trim() && !image)) return
    setBusy(true); setError('')
    try {
      let body = { text: text.trim() }
      if (image) { body = new FormData(); body.set('text', text.trim()); body.set('image', image) }
      const message = await communicationRequest(`${path}messages/`, { method: 'POST', body })
      setMessages(current => mergeMessages(current, [message])); setText(''); setImage(null)
      if (fileInput.current) fileInput.current.value = ''
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }
  async function older() {
    setPaging(true)
    try {
      const data = await communicationRequest(`${path}messages/`, { query: { cursor } })
      setMessages(current => mergeMessages(current, items(data))); setCursor(data.next ? new URL(data.next, window.location.origin).searchParams.get('cursor') : null)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setPaging(false) }
  }
  async function changeLanguage(event) {
    setChanging(true); setError('')
    try { setRoom(await communicationRequest(`${path}translation/`, { method: 'PATCH', body: { language: event.target.value } })) }
    catch (failure) { setError(errorMessage(failure)) }
    finally { setChanging(false) }
  }
  async function call() {
    setError('')
    try { setPhone((await communicationRequest(`${path}call/`)).phone) }
    catch (failure) { setError(errorMessage(failure)) }
  }
  async function leave() {
    if (!window.confirm('이 채팅방에서 나가시겠습니까?')) return
    try { await communicationRequest(path, { method: 'DELETE' }); onClose() }
    catch (failure) { setError(errorMessage(failure)) }
  }
  const Icon = room.counterpart?.is_employer ? Building2 : UserRound
  return <HomeDialog title={room.counterpart?.name || '대화'} onClose={onClose} wide><div className="comm-chat">
    <div className="comm-chat-header"><span className="comm-avatar"><Icon size={22} /></span><div><strong>{room.counterpart?.name}</strong><small>{room.counterpart?.is_online ? '온라인' : '오프라인'} · {connected ? '실시간 연결' : '주기적으로 새 메시지 확인'}</small></div><button type="button" aria-label="전화 연결" onClick={call}><Phone size={20} /></button><button type="button" aria-label="대화 설정" aria-expanded={settings} onClick={() => setSettings(value => !value)}><Menu size={20} /></button></div>
    {room.job && <p className="comm-chat-job">{room.job.title}</p>}
    {phone && <a className="comm-call" href={`tel:${phone.replace(/[^+0-9]/g, '')}`}>{phone} 전화 걸기</a>}
    {settings && <div className="comm-chat-settings"><FormSelect label="내 번역 언어" name="language" value={room.my_language || 'ko'} onChange={changeLanguage} disabled={changing} options={languages.map(language => ({ value: language.code, label: language.native_name }))} /><button className="comm-danger" onClick={leave}>채팅방 나가기</button></div>}
    <div className="comm-chat-tabs" aria-label="메시지 표시 방식"><button aria-pressed={!translated} onClick={() => setTranslated(false)}>원문 보기</button><button aria-pressed={translated} onClick={() => setTranslated(true)}>번역과 함께</button></div>
    {error && <p className="comm-error" role="alert">{error}</p>}
    <div className="comm-messages" aria-label="대화 내용">
      {loading ? <p role="status">대화를 불러오는 중…</p> : !user ? <button onClick={() => { setLoading(true); setError(''); setRetry(value => value + 1) }}>대화 다시 불러오기</button> : null}
      {cursor && <button className="comm-history" disabled={paging} onClick={older}>{paging ? '불러오는 중…' : '이전 대화 보기'}</button>}
      {!loading && user && !messages.length && <p className="comm-state">첫 메시지를 보내보세요.</p>}
      {messages.map(message => <div key={message.id} className={`comm-message ${message.sender === user?.id ? 'is-mine' : ''}`}>
        <div className="comm-bubble">{message.image && <a href={message.image} target="_blank" rel="noreferrer"><img src={message.image} alt="대화 첨부 사진" /></a>}{message.text && <p>{message.text}</p>}{translated && message.translations?.[room.my_language] && message.translations[room.my_language] !== message.text && <p className="comm-message-translation">{message.translations[room.my_language]}</p>}</div>
        <time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</time>
      </div>)}<div ref={bottom} />
    </div>
    <form className="comm-composer" onSubmit={send}>
      {image && <div className="comm-attachment">{image.name}<button type="button" onClick={() => { setImage(null); fileInput.current.value = '' }}>첨부 취소</button></div>}
      <div className="comm-composer-row"><label className="comm-attach"><ImagePlus size={22} /><span className="home-sr-only">사진 첨부</span><input ref={fileInput} type="file" accept="image/*" disabled={busy} onChange={event => setImage(event.target.files?.[0] || null)} /></label><input aria-label="메시지" placeholder="메시지를 입력하세요" value={text} maxLength={2000} disabled={busy || !user} onChange={event => setText(event.target.value)} /><button type="submit" aria-label="메시지 보내기" disabled={busy || !user || (!text.trim() && !image)}><Send size={19} /></button></div>
      <div className="comm-quick-replies">{replies.map(reply => <button key={reply.id} type="button" disabled={busy} onClick={() => setText(reply.text)}>{reply.text}</button>)}</div>
    </form>
  </div></HomeDialog>
}
