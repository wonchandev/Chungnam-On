import { Link } from 'react-router-dom'
import Navigation from './Navigation.jsx'
import useHomeSession from '../pages/Home/hooks/useHomeSession.js'
import AccountMenu from './account/AccountMenu.jsx'

export default function Header() {
  const { session } = useHomeSession()
  return (
    <header className="site-header">
      <Link className="brand" to="/">충남온</Link>
      <Navigation />
      <nav className="header-auth" aria-label="계정 메뉴">
        {session ? <AccountMenu /> : <><Link to="/login">로그인</Link><Link className="header-signup" to="/signup">회원가입</Link></>}
      </nav>
    </header>
  )
}
