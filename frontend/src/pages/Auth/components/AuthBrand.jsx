import { Link } from 'react-router-dom'

export default function AuthBrand() {
  return <Link to="/" className="auth-brand" aria-label="충남온 홈으로 이동">
    <img className="auth-wordmark" src="/brand/wordmark.svg" alt="CHUNGNAM ON" width="776" height="75" />
    <img className="auth-logo" src="/brand/logo.svg" alt="" width="505" height="306" />
  </Link>
}
