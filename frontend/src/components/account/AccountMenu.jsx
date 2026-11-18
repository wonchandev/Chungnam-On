import { useEffect, useRef, useState } from 'react'
import { LogOut, UserRound, UserRoundPen } from 'lucide-react'
import { Link } from 'react-router-dom'
import useHomeSession from '../../pages/Home/hooks/useHomeSession.js'
import './account.css'

export default function AccountMenu() {
  const { logout } = useHomeSession()
  const [open, setOpen] = useState(false)
  const root = useRef(null)
  const trigger = useRef(null)
  useEffect(() => {
    if (!open) return
    function outside(event) { if (!root.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  return <div className="account-menu" ref={root} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }} onKeyDown={event => {
    if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() }
  }}>
    <button ref={trigger} className="account-trigger" type="button" aria-label="내 계정" aria-expanded={open} aria-controls="account-options" onClick={() => setOpen(value => !value)}><UserRound size={21} aria-hidden="true" /></button>
    {open && <div id="account-options" className="account-options">
      <Link to="/mypage" onClick={() => setOpen(false)}><UserRoundPen size={18} aria-hidden="true" />마이페이지</Link>
      <button type="button" onClick={async () => { if (await logout()) setOpen(false) }}><LogOut size={18} aria-hidden="true" />로그아웃</button>
    </div>}
  </div>
}
