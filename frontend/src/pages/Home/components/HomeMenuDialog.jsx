import { Link } from 'react-router-dom'
import { ArrowRight, LogOut } from 'lucide-react'
import HomeDialog from './HomeDialog.jsx'

const links = [
  { to: '/jobs', label: '구인구직' },
  { to: '/nearby-jobs', label: '내 주변 일자리' },
  { to: '/communication', label: '다국어 소통' },
  { to: '/administration', label: '행정 관리' },
]

export default function HomeMenuDialog({ session, onClose, onLogin, onLogout }) {
  return (
    <HomeDialog title="전체 메뉴" onClose={onClose}>
      <nav className="home-menu" aria-label="전체 메뉴">
        {links.map(({ to, label }) => <Link key={to} to={to}>{label}<ArrowRight size={18} /></Link>)}
        {session
          ? <button type="button" onClick={onLogout}>로그아웃<LogOut size={18} /></button>
          : <button type="button" onClick={onLogin}>로그인<ArrowRight size={18} /></button>}
      </nav>
    </HomeDialog>
  )
}
