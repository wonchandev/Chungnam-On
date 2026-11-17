import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../../../api/client.js'
import useHomeResource from '../hooks/useHomeResource.js'

function MemberAccount({ session, onRefresh, onLogin }) {
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const update = () => setRevision(value => value + 1)
    window.addEventListener('profile-updated', update)
    return () => window.removeEventListener('profile-updated', update)
  }, [])
  const load = useCallback(signal => {
    void revision
    return apiRequest('auth/me/', { signal, accessToken: session.access, refreshToken: session.refresh, onRefresh })
  }, [session, onRefresh, revision])
  const profile = useHomeResource(load)
  return <div className="home-account">
    <div><strong>{profile.data ? `${profile.data.name || profile.data.username}님, 반가워요` : '내 계정'}</strong>
      <p>{profile.error ? '계정 정보를 불러오지 못했어요.' : profile.loading ? '계정 정보를 확인하고 있어요.' : profile.data?.role === 'employer' ? '지역의 일자리와 근로자를 연결해 보세요.' : '관심 공고를 저장하고 나에게 맞는 일자리를 찾아보세요.'}</p>
    </div>
    {profile.error && (profile.error.status === 401 ? <button type="button" onClick={onLogin}>다시 로그인</button> : <button type="button" onClick={profile.retry}>다시 시도</button>)}
  </div>
}

export default function HomeAccount({ session, onRefresh, onLogin }) {
  return session ? <MemberAccount session={session} onRefresh={onRefresh} onLogin={onLogin} /> : <div className="home-account">
    <div><strong>충남에서 나에게 맞는 일자리를 찾아보세요</strong><p>일자리는 바로 둘러보고, 로그인하면 관심 공고 저장과 맞춤 추천을 이용할 수 있어요.</p></div>
    <div className="home-account-actions"><Link to="/login">로그인</Link><Link to="/signup">회원가입</Link></div>
  </div>
}
