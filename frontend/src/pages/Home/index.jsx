import { useCallback, useState } from 'react'
import { homeApi } from './api/home.js'
import useHomeResource from './hooks/useHomeResource.js'
import useHomeSession from './hooks/useHomeSession.js'
import HomeToolbar from './components/HomeToolbar.jsx'
import HomeSearch from './components/HomeSearch.jsx'
import HomeFeed from './components/HomeFeed.jsx'
import HomeMenuDialog from './components/HomeMenuDialog.jsx'
import DetailDialog from './components/DetailDialog.jsx'
import LoginDialog from './components/LoginDialog.jsx'
import './styles/home.css'

export default function HomePage() {
  const [region, setRegion] = useState('')
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [detailId, setDetailId] = useState(null)
  const [loginOpen, setLoginOpen] = useState(false)
  const { session, saveSession, notice, login, logout } = useHomeSession()
  const regionLoad = useCallback((signal) => homeApi.regions({ signal }), [])
  const regions = useHomeResource(regionLoad)

  function handleLogin(tokens) {
    login(tokens)
    setLoginOpen(false)
  }

  async function handleLogout() {
    if (await logout()) setMenuOpen(false)
  }

  return (
    <div className="home-page">
      <h1 className="home-title">홈</h1>
      <HomeToolbar
        region={region}
        regions={regions}
        onRegionChange={setRegion}
        searchOpen={searchOpen}
        onSearchToggle={() => setSearchOpen(!searchOpen)}
        menuOpen={menuOpen}
        onMenuOpen={() => setMenuOpen(true)}
      />
      {searchOpen && <HomeSearch query={query} onSearch={setQuery} />}
      <HomeFeed
        key={`${region}:${query}:${session?.access || ''}`}
        region={region}
        query={query}
        session={session}
        onOpen={setDetailId}
        onLogin={() => setLoginOpen(true)}
        onRefresh={saveSession}
      />
      <p className="home-sr-only" role="status">{notice}</p>
      {menuOpen && (
        <HomeMenuDialog
          session={session}
          onClose={() => setMenuOpen(false)}
          onLogin={() => { setMenuOpen(false); setLoginOpen(true) }}
          onLogout={handleLogout}
        />
      )}
      {detailId !== null && <DetailDialog id={detailId} session={session} onClose={() => setDetailId(null)} onRefresh={saveSession} />}
      {loginOpen && <LoginDialog onClose={() => setLoginOpen(false)} onLogin={handleLogin} />}
    </div>
  )
}
