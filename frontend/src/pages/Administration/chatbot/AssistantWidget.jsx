import { useState } from 'react'
import { Bot, Sparkles } from 'lucide-react'
import useHomeSession from '../../Home/hooks/useHomeSession.js'
import LoginDialog from '../../Home/components/LoginDialog.jsx'
import AssistantPanel from './AssistantPanel.jsx'
import useAssistantChat from './useAssistantChat.js'
import './assistant.css'

function MemberAssistant({ open, onClose, onGuide }) {
  const chat = useAssistantChat()
  return open ? <AssistantPanel chat={chat} onClose={onClose} onGuide={onGuide} /> : null
}
export default function AssistantWidget({ onGuide }) {
  const { session, login } = useHomeSession()
  const [open, setOpen] = useState(false)
  return <>
    <div className="assistant-launcher"><span className="assistant-launcher-label"><Sparkles size={13} aria-hidden="true" />궁금한 건 AI 도우미에게</span><button className="assistant-launcher-button" type="button" aria-label="충남온 AI 도우미 열기" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}><Bot size={28} strokeWidth={1.7} aria-hidden="true" /><span>AI</span></button></div>
    {session ? <MemberAssistant open={open} onClose={() => setOpen(false)} onGuide={onGuide} /> : open && <LoginDialog message="AI 생활·행정 상담을 이용하려면 로그인해 주세요." onClose={() => setOpen(false)} onLogin={login} />}
  </>
}
