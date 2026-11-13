import { NavLink } from 'react-router-dom'
import { House, MapPin, MessageCircle, ClipboardList, UserRound } from 'lucide-react'

const navigation = [
  { to: '/', label: '홈', icon: House },
  { to: '/nearby-jobs', label: '내 주변 일자리', icon: MapPin },
  { to: '/communication', label: '다국어 소통', icon: MessageCircle },
  { to: '/administration', label: '행정 관리', icon: ClipboardList },
  { to: '/jobs', label: '구인구직', icon: UserRound },
]

export default function Navigation() {
  return (
    <nav className="navigation" aria-label="주 메뉴">
      {navigation.map(({ to, label, icon }) => {
        const Icon = icon
        return (
          <NavLink key={to} to={to} end={to === '/'} aria-label={label} title={label}>
            <Icon className="navigation-icon" size={24} strokeWidth={2.5} aria-hidden="true" />
            <span className="navigation-label">{label}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}

