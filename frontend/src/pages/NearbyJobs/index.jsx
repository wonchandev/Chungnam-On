import { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Flame, LocateFixed } from 'lucide-react'
import { apiGet } from '../../api/client.js'
import useHomeSession from '../Home/hooks/useHomeSession.js'
import DetailDialog from '../Home/components/DetailDialog.jsx'
import LoginDialog from '../Home/components/LoginDialog.jsx'
import { money, payLabel } from '../Home/utils/formatters.js'
import './nearby.css'

const CHEONAN = [36.8151, 127.1139]
const short = (amount) => amount >= 10000 ? `${Math.round(amount / 1000) / 10}만` : money(amount)

export default function NearbyJobsPage() {
  const { session, saveSession, login } = useHomeSession()
  const box = useRef(null)
  const map = useRef(null)
  const layer = useRef(null)
  const [jobs, setJobs] = useState([])
  const [urgentOnly, setUrgentOnly] = useState(false)
  const [selected, setSelected] = useState(null)
  const [detailId, setDetailId] = useState(null)
  const [loginOpen, setLoginOpen] = useState(false)
  const [error, setError] = useState('')
  const [locating, setLocating] = useState(false)
  const urgentRef = useRef(false)
  useEffect(() => { urgentRef.current = urgentOnly }, [urgentOnly])

  const refresh = useCallback(async () => {
    const m = map.current
    if (!m) return
    const b = m.getBounds()
    try {
      const data = await apiGet('jobs/map/', { query: { sw_lat: b.getSouth(), sw_lng: b.getWest(), ne_lat: b.getNorth(), ne_lng: b.getEast(), urgent: urgentRef.current ? 'true' : '' } })
      setJobs(data.results || []); setError('')
    } catch { setError('주변 일자리를 불러오지 못했어요.') }
  }, [])

  useEffect(() => {
    const m = L.map(box.current, { zoomControl: true }).setView(CHEONAN, 12)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18, attribution: '© OpenStreetMap' }).addTo(m)
    layer.current = L.layerGroup().addTo(m)
    map.current = m
    let timer
    m.on('moveend', () => { clearTimeout(timer); timer = setTimeout(refresh, 250) })
    refresh()
    return () => { clearTimeout(timer); m.remove(); map.current = null }
  }, [refresh])

  useEffect(() => { refresh() }, [urgentOnly, refresh])

  useEffect(() => {
    const group = layer.current
    if (!group) return
    group.clearLayers()
    jobs.forEach((job) => {
      const icon = L.divIcon({ className: '', html: `<span class="nearby-pin${job.is_urgent ? ' is-urgent' : ''}">${short(job.pay_amount)}</span>`, iconSize: [52, 28], iconAnchor: [26, 28] })
      L.marker([job.lat, job.lng], { icon, title: job.title }).on('click', () => setSelected(job)).addTo(group)
    })
  }, [jobs])

  function locate() {
    if (!navigator.geolocation) { setError('이 브라우저에서는 위치를 사용할 수 없어요.'); return }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => { map.current?.setView([pos.coords.latitude, pos.coords.longitude], 13); setLocating(false) },
      () => { setError('위치 권한을 허용해 주세요.'); setLocating(false) },
      { timeout: 8000 },
    )
  }

  return <div className="nearby-page">
    <header className="nearby-head"><h1>내 주변 일자리</h1><p>지도에서 가까운 일자리를 찾아보세요</p></header>
    <div className="nearby-tools">
      <button type="button" className={urgentOnly ? 'is-active' : ''} aria-pressed={urgentOnly} onClick={() => setUrgentOnly(!urgentOnly)}><Flame size={15} aria-hidden="true" />긴급만</button>
      <button type="button" onClick={locate} disabled={locating}><LocateFixed size={15} aria-hidden="true" />{locating ? '찾는 중…' : '내 위치'}</button>
      <span>이 지역 공고 {jobs.length}건</span>
    </div>
    <div className="nearby-map" ref={box} role="region" aria-label="일자리 지도" />
    {error && <p className="nearby-error" role="alert">{error}</p>}
    {selected && <div className="nearby-selected" role="status"><div><strong>{selected.title}</strong><small>{payLabel(selected.pay_type)} {money(selected.pay_amount)}원{selected.is_urgent ? ' · 긴급' : ''}</small></div><button type="button" onClick={() => setDetailId(selected.id)}>상세보기</button></div>}
    <h2 className="nearby-list-title">목록 보기</h2>
    {jobs.length ? <ul className="nearby-list">{jobs.map((job) => <li key={job.id}><button type="button" onClick={() => { setSelected(job); map.current?.panTo([job.lat, job.lng]) }}><strong>{job.title}</strong><span>{payLabel(job.pay_type)} {money(job.pay_amount)}원</span></button><button type="button" className="nearby-detail" onClick={() => setDetailId(job.id)}>상세</button></li>)}</ul> : <p className="nearby-empty">이 지역에는 공고가 없어요. 지도를 움직여 보세요.</p>}
    {detailId !== null && <DetailDialog id={detailId} session={session} onClose={() => setDetailId(null)} onRefresh={saveSession} onLogin={() => setLoginOpen(true)} />}
    {loginOpen && <LoginDialog message="로그인이 필요해요." onClose={() => setLoginOpen(false)} onLogin={(tokens) => { login(tokens); setLoginOpen(false) }} />}
  </div>
}
