import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { apiGet } from '../../api/client.js'
import { payLabel, timeLabel } from '../Jobs/format.js'
import './nearby.css'

const CENTER = [36.65, 126.85]
const CLUSTER_MAX_ZOOM = 11

const QUICK = [
  { label: '1일 급구', urgent: true },
  { label: '매장관리 및 판매', category: 'retail' },
  { label: '생산, 건설, 노무', category: 'construction' },
]

const TAGS = [
  { key: 'beginner_ok', label: '초보가능' },
  { key: 'with_friend', label: '친구와 함께' },
  { key: 'lunch_provided', label: '점심 제공' },
  { key: 'local_preferred', label: '인근지역우대' },
  { key: 'night_shift', label: '야간근무' },
]

const manwon = (n) => `${Math.round(n / 1000) / 10}만`

export default function NearbyJobsPage() {
  const navigate = useNavigate()
  const elRef = useRef(null)
  const mapRef = useRef(null)
  const layerRef = useRef(null)

  const [view, setView] = useState(null)
  const [urgent, setUrgent] = useState(false)
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState([])
  const [data, setData] = useState(null)
  const [showList, setShowList] = useState(false)
  const [list, setList] = useState({ jobs: [], count: 0 })
  const [error, setError] = useState('')

  const filterQuery = useMemo(
    () => ({
      urgent: urgent || undefined,
      category,
      ...Object.fromEntries(tags.map((t) => [t, true])),
    }),
    [urgent, category, tags],
  )

  // 지도 만들기 (한 번만)
  useEffect(() => {
    const map = L.map(elRef.current, { zoomControl: false }).setView(CENTER, 9)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    const sync = () => {
      const b = map.getBounds()
      setView({
        zoom: map.getZoom(),
        sw_lat: b.getSouth(),
        sw_lng: b.getWest(),
        ne_lat: b.getNorth(),
        ne_lng: b.getEast(),
      })
    }
    map.on('moveend', sync)
    map.whenReady(sync)

    return () => {
      map.remove()
      mapRef.current = null
      layerRef.current = null
    }
  }, [])

  // 지도 영역·필터가 바뀔 때 클러스터/마커 불러오기
  useEffect(() => {
    if (!view) return undefined
    const controller = new AbortController()
    const kind = view.zoom < CLUSTER_MAX_ZOOM ? 'clusters' : 'markers'
    const bbox = `${view.sw_lat},${view.sw_lng},${view.ne_lat},${view.ne_lng}`
    apiGet(kind === 'clusters' ? 'jobs/map/clusters/' : 'jobs/map/', {
      signal: controller.signal,
      query: { ...view, bbox, ...filterQuery },
    })
      .then((res) => {
        setError('')
        setData({
          kind,
          items: kind === 'clusters' ? res.clusters : res.results,
        })
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => controller.abort()
  }, [view, filterQuery])

  // 지도에 그리기
  useEffect(() => {
    const layer = layerRef.current
    const map = mapRef.current
    if (!layer || !map || !data) return
    layer.clearLayers()
    data.items.forEach((item) => {
      if (data.kind === 'clusters') {
        const size = Math.min(48 + item.count * 3, 96)
        L.marker([item.lat, item.lng], {
          icon: L.divIcon({
            className: 'nm-wrap',
            html: `<div class="nm-cluster" style="width:${size}px;height:${size}px">${item.count}</div>`,
            iconSize: [size, size],
          }),
        })
          .on('click', () => map.setView([item.lat, item.lng], map.getZoom() + 2))
          .addTo(layer)
      } else {
        L.marker([item.lat, item.lng], {
          icon: L.divIcon({
            className: 'nm-wrap',
            html: `<div class="nm-pin${item.is_urgent ? ' urgent' : ''}">${manwon(item.pay_amount)}</div>`,
            iconSize: [64, 28],
            iconAnchor: [32, 14],
          }),
        })
          .on('click', () => navigate(`/jobs?id=${item.id}`))
          .addTo(layer)
      }
    })
  }, [data, navigate])

  // 목록 보기
  useEffect(() => {
    if (!showList || !view) return undefined
    const controller = new AbortController()
    const bbox = `${view.sw_lat},${view.sw_lng},${view.ne_lat},${view.ne_lng}`
    apiGet('jobs/', { signal: controller.signal, query: { bbox, ...filterQuery } })
      .then((res) => setList({ jobs: res.results, count: res.count }))
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => controller.abort()
  }, [showList, view, filterQuery])

  const toggleQuick = (q) => {
    if (q.urgent) setUrgent((v) => !v)
    else setCategory((c) => (c === q.category ? '' : q.category))
  }

  const toggleTag = (key) =>
    setTags((prev) => (prev.includes(key) ? prev.filter((t) => t !== key) : [...prev, key]))

  const locate = () => {
    navigator.geolocation?.getCurrentPosition(
      (p) => mapRef.current?.setView([p.coords.latitude, p.coords.longitude], 12),
      () => setError('위치 권한을 허용해 주세요.'),
    )
  }

  const quickOn = (q) => (q.urgent ? urgent : category === q.category)

  return (
    <div className="nm-page">
      <div className="nm-mapbox">
        <div ref={elRef} className="nm-map" />
        <div className="nm-top">
          {QUICK.map((q) => (
            <button
              key={q.label}
              type="button"
              className={`nm-chip${quickOn(q) ? ' on' : ''}`}
              onClick={() => toggleQuick(q)}
            >
              {q.label}
            </button>
          ))}
        </div>
        <button type="button" className="nm-locate" onClick={locate}>
          내 위치
        </button>
        <button type="button" className="nm-list-btn" onClick={() => setShowList((v) => !v)}>
          {showList ? '지도만 보기' : '목록보기'}
        </button>
      </div>

      <div className="nm-tags">
        {TAGS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`nm-tag${tags.includes(t.key) ? ' on' : ''}`}
            onClick={() => toggleTag(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p role="alert">{error}</p>}

      {showList && (
        <>
          <p className="nm-total">총 {list.count}건</p>
          <ul className="nm-list">
            {list.jobs.map((job) => (
              <li key={job.id}>
                <Link to={`/jobs?id=${job.id}`} className="nm-card">
                  <span className="nm-company">{job.company_name}</span>
                  <strong className="nm-title">{job.title}</strong>
                  <span className="nm-info">
                    {job.region.name} · {timeLabel(job)}
                  </span>
                  <span className="nm-pay">{payLabel(job)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
