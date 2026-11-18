import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, History, Plus, Send, ShieldCheck, Sparkles } from 'lucide-react'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import AssistantMessage from './AssistantMessage.jsx'
import ConversationHistory from './ConversationHistory.jsx'

const starters = ['체류기간 연장은 어떻게 하나요?', '건강보험 가입 방법이 궁금해요', '근로계약서에서 무엇을 확인하나요?', '임금을 받지 못했을 때 어떻게 하나요?']
export default function AssistantPanel({ chat, onClose, onGuide }) {
  const [history, setHistory] = useState(false)
  const bottom = useRef(null)
  const input = useRef(null)
  const thread = useRef(null)
  useEffect(() => {
    if (history) return
    if (!chat.messages.length && !chat.busy) { if (thread.current) thread.current.scrollTop = 0; return }
    bottom.current?.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  }, [chat.messages.length, chat.busy, history])
  async function selectConversation(id) { if (await chat.openConversation(id)) setHistory(false) }
  function submit(event) { event.preventDefault(); chat.send() }
  return <HomeDialog title="충남온 AI 도우미" onClose={onClose} className="assistant-panel">
    <div className="assistant-intro-line"><span><span className="assistant-online-dot" />생활·행정 정보를 함께 찾아드려요</span><span className="assistant-ai-badge"><Sparkles size={11} /> AI</span></div>
    <div className="assistant-toolbar"><button type="button" disabled={chat.busy || chat.loading} onClick={() => { chat.newConversation(); setHistory(false); input.current?.focus() }}><Plus size={15} />새 대화</button><button type="button" disabled={chat.busy || chat.loading} aria-pressed={history} onClick={() => setHistory(value => !value)}>{history ? <ArrowLeft size={15} /> : <History size={15} />}{history ? '대화로 돌아가기' : '이전 대화'}</button></div>
    {chat.error && <div className="assistant-error" role="alert">{chat.error}{!history && <button type="button" onClick={() => setHistory(true)}>이전 대화 확인</button>}</div>}
    {history ? <div className="assistant-scroll"><ConversationHistory key={chat.historyVersion} onSelect={selectConversation} loading={chat.loading} /></div> : <>
      <div ref={thread} className="assistant-scroll" aria-label="AI 상담 대화">
        {!chat.messages.length && <div className="assistant-welcome"><span className="assistant-welcome-avatar"><Bot size={35} strokeWidth={1.6} /></span><span className="assistant-eyebrow">CHUNGNAM ON ASSISTANT</span><h3>어떤 도움이 필요하세요?</h3><p>비자·보험·근로 등 궁금한 정보를<br />등록된 행정 안내를 바탕으로 찾아드려요.</p><div className="assistant-starters">{starters.map(text => <button type="button" key={text} onClick={() => chat.send(text)} disabled={chat.busy}><MessagePrompt text={text} /></button>)}</div></div>}
        {chat.conversation && <p className="assistant-conversation-title">{chat.conversation.title}</p>}
        {chat.messages.map(message => <AssistantMessage key={message.id} message={message} onGuide={onGuide} onFeedback={chat.updateFeedback} />)}
        {chat.busy && <div className="assistant-thinking" role="status"><Bot size={17} /><span>관련 안내를 찾아 답변하고 있어요</span><span className="assistant-dots" aria-hidden="true">•••</span></div>}
        {chat.masked && <p className="assistant-masked" role="status"><ShieldCheck size={14} />입력한 개인정보를 가리고 처리했어요.</p>}
        {!chat.busy && !!chat.suggestions.length && <div className="assistant-suggestions" aria-label="이어 물어보기">{chat.suggestions.map(text => <button type="button" key={text} onClick={() => chat.send(text)}>{text}</button>)}</div>}
        <div ref={bottom} />
      </div>
      <form className="assistant-composer" onSubmit={submit}><label className="home-sr-only" htmlFor="assistant-question">챗봇에게 질문하기</label><div><textarea ref={input} id="assistant-question" rows={2} value={chat.draft} onChange={event => chat.setDraft(event.target.value)} maxLength={2000} placeholder="궁금한 내용을 입력하세요" disabled={chat.busy} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); if (chat.draft.trim() && !chat.busy) chat.send() } }} /><button type="submit" disabled={chat.busy || !chat.draft.trim()} aria-label="질문 보내기"><Send size={19} /></button></div><span className="assistant-character-count">{chat.draft.length.toLocaleString()} / 2,000</span><p>중요한 사항은 공식 출처에서 확인해 주세요.<br />여권번호·외국인등록번호는 입력하지 마세요.</p></form>
    </>}
  </HomeDialog>
}

function MessagePrompt({ text }) { return <><span>{text}</span><Send size={13} aria-hidden="true" /></> }
