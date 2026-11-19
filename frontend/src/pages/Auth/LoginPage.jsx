import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthBrand from './components/AuthBrand.jsx'
import LoginForm from './components/LoginForm.jsx'
import { saveSession } from '../../api/session.js'

export default function LoginPage() {
  const navigate = useNavigate()
  const { state } = useLocation()
  useEffect(() => {
    document.title = '로그인 | 충남온'
    return () => { document.title = '충남온 | 일자리와 생활을 연결하다' }
  }, [])
  function login(tokens) {
    saveSession(tokens)
    navigate(state?.from === '/mypage' ? '/mypage' : '/', { replace: true })
  }
  return <section className="auth-page">
    <AuthBrand />
    <h1>로그인</h1>
    <p role="status">{state?.signupComplete ? '회원가입이 완료되었습니다. 자동 로그인에 실패했으니 직접 로그인해 주세요.' : state?.from === '/mypage' ? '마이페이지를 이용하려면 로그인해 주세요.' : '아이디로 로그인해 주세요.'}</p>
    <LoginForm onSuccess={login} initialUsername={state?.username || ''} />
    <Link to="/signup">계정이 없나요? 회원가입</Link>
  </section>
}
