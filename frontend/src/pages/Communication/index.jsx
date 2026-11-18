import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Camera, Headphones, Languages, Mic, MessageCircle } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import useHomeSession from '../Home/hooks/useHomeSession.js'
import useHomeResource from '../Home/hooks/useHomeResource.js'
import LoginDialog from '../Home/components/LoginDialog.jsx'
import CourseCards from './components/CourseCards.jsx'
import RecentChats from './components/RecentChats.jsx'
import TranslationDialog from './components/TranslationDialog.jsx'
import PhrasesDialog from './components/PhrasesDialog.jsx'
import LiveVoiceDialog from './components/LiveVoiceDialog.jsx'
import ChatDialog from './components/ChatDialog.jsx'
import Community from './components/Community.jsx'
import SegmentedControl from './components/SegmentedControl.jsx'
import { communicationRequest } from './api.js'
import './communication.css'

export default function CommunicationPage() {
  const { session, login } = useHomeSession()
  const [panel, setPanel] = useState(null)
  const [pending, setPending] = useState(null)
  const [loginOpen, setLoginOpen] = useState(false)
  const location = useLocation()
  const [chatRoom, setChatRoom] = useState(() => location.state?.roomId ? { id: location.state.roomId } : null) // 공고 상세의 문의·지원 후 바로 채팅 열기
  const [section, setSection] = useState('chats')
  const loadLanguages = useCallback(signal => communicationRequest('languages/', { signal }), [])
  const languages = useHomeResource(loadLanguages)
  const loadFeatures = useCallback(signal => communicationRequest('features/', { signal }), [])
  const features = useHomeResource(loadFeatures).data || {} // API 키가 필요한 기능은 사용 가능할 때만 노출
  useEffect(() => { document.title = '다국어 소통 | 충남온'; return () => { document.title = '충남온 | 일자리와 생활을 연결하다' } }, [])
  function open(name) {
    if (!session && name !== 'phrases') { setPending(name); setLoginOpen(true); return }
    setPanel(name)
  }
  const tools = [features.voice_translate && { name: 'voice', title: '음성 번역', description: '말을 녹음해서 번역', Icon: Mic }, features.image_translate && { name: 'image', title: '사진 번역', description: '사진 속 글자 번역', Icon: Camera }, { name: 'phrases', title: '현장 필수 표현', description: '일할 때 쓰는 문장', Icon: Languages }, { name: 'text', title: '텍스트 번역', description: '입력한 문장 번역', Icon: MessageCircle }].filter(Boolean)
  return <div className="comm-page">
    <header className="comm-page-heading"><div><span>COMMUNICATION</span><h1>다국어 소통</h1><p>언어가 달라도, 마음은 통하도록</p></div><span className="comm-heading-icon"><Languages size={30} aria-hidden="true" /></span></header>
    <CourseCards key={session ? 'member' : 'guest'} session={session} onLogin={() => { setPending(null); setLoginOpen(true) }} />
    {features.live_voice && <button className="comm-live-banner" onClick={() => open('live')}><span className="comm-live-icon"><Headphones size={30} aria-hidden="true" /></span><span><strong>AI 실시간 현장 통역</strong><small>말하는 순간, 서로의 언어로</small></span><ArrowRight size={22} aria-hidden="true" /></button>}
    <div className="comm-tools">{tools.map(tool => <button key={tool.name} onClick={() => open(tool.name)}><tool.Icon size={22} aria-hidden="true" /><strong>{tool.title}</strong><span>{tool.description}</span></button>)}</div>
    {languages.error && <div className="comm-state" role="alert">언어 목록을 불러오지 못했어요. <button onClick={languages.retry}>다시 시도</button></div>}
    <SegmentedControl id="comm-space" label="소통 공간" value={section} onChange={setSection} options={[{ value: 'chats', label: '최근 대화' }, { value: 'community', label: '커뮤니티' }]} />
    <div id="comm-space-panel" role="tabpanel" aria-labelledby={`comm-space-${section}`}>
      {section === 'community' ? <Community session={session} onLogin={() => { setPending(null); setLoginOpen(true) }} /> : session ? <RecentChats languages={languages.data || []} /> : <><div className="comm-section-heading"><h2>최근 대화</h2></div><div className="comm-login-card"><MessageCircle size={30} aria-hidden="true" /><strong>대화를 이어가려면 로그인해 주세요</strong><p>사업주와의 대화와 번역 내용을 한곳에서 확인하세요.</p><div><button className="comm-primary" onClick={() => { setPending(null); setLoginOpen(true) }}>로그인</button><Link to="/signup">회원가입</Link></div></div></>}
    </div>
    {['text', 'voice', 'image'].includes(panel) && <TranslationDialog mode={panel} tts={!!features.tts} languages={languages.data || []} onClose={() => setPanel(null)} />}
    {chatRoom && session && <ChatDialog initialRoom={chatRoom} languages={languages.data || []} onClose={() => { setChatRoom(null); window.history.replaceState({}, '') }} />}
    {panel === 'phrases' && <PhrasesDialog languages={languages.data || []} onClose={() => setPanel(null)} />}
    {panel === 'live' && <LiveVoiceDialog languages={languages.data || []} onClose={() => setPanel(null)} />}
    {loginOpen && <LoginDialog message="번역·교육 신청·대화·커뮤니티 활동을 이용하려면 로그인해 주세요." onClose={() => { setLoginOpen(false); setPending(null) }} onLogin={tokens => { login(tokens); setLoginOpen(false); if (pending) setPanel(pending); setPending(null) }} />}
  </div>
}
