import { Link } from 'react-router-dom'
import HomeDialog from './HomeDialog.jsx'
import LoginForm from '../../Auth/components/LoginForm.jsx'
import '../../Auth/auth.css'

export default function LoginDialog({ onClose, onLogin, message = '관심 공고를 저장하려면 로그인해 주세요.' }) {
  return <HomeDialog title="로그인" onClose={onClose}>
    <div className="auth-page">
      <p>{message}</p>
      <LoginForm onSuccess={onLogin} />
      <Link to="/signup">계정이 없나요? 회원가입</Link>
    </div>
  </HomeDialog>
}
