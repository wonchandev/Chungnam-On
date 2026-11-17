import { Link, Outlet, Route, Routes } from 'react-router-dom'
import Header from './components/Header.jsx'
import HomePage from './pages/Home'
import CommunicationPage from './pages/Communication'
import AdministrationPage from './pages/Administration'
import NearbyJobsPage from './pages/NearbyJobs'
import JobsPage from './pages/Jobs'
import AuthPage from './pages/Auth'

function Layout() {
  return (
    <>
      <a className="skip-link" href="#main-content">본문으로 이동</a>
      <Header />
      <main id="main-content"><Outlet /></main>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="login" element={<AuthPage mode="login" />} />
        <Route path="signup" element={<AuthPage mode="signup" />} />
        <Route index element={<HomePage />} />
        <Route path="communication" element={<CommunicationPage />} />
        <Route path="administration" element={<AdministrationPage />} />
        <Route path="nearby-jobs" element={<NearbyJobsPage />} />
        <Route path="jobs" element={<JobsPage />} />
        <Route path="*" element={<section><h1>페이지를 찾을 수 없습니다</h1><Link to="/">홈으로 이동</Link></section>} />
      </Route>
    </Routes>
  )
}
