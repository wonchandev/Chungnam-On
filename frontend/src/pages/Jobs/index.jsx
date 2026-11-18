import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Search,
  User,
  Building2,
  Crown,
  ChevronRight,
  Factory,
  HardHat,
  Sprout,
  Truck,
} from 'lucide-react'
import JobList from './JobList.jsx'
import JobDetail from './JobDetail.jsx'
import './jobs.css'

const QUICK_MENUS = [
  { label: '일자리 찾기', icon: Search, list: true },
  { label: '내 구직활동', icon: User },
  { label: '인력사무소', icon: Building2 },
  { label: '관심 공고', icon: Crown },
]

const POPULAR_CATEGORIES = [
  { label: '제조 생산', icon: Factory, code: 'manufacturing' },
  { label: '건설 현장', icon: HardHat, code: 'construction' },
  { label: '농업, 축산', icon: Sprout, code: 'agriculture' },
  { label: '물류,배송', icon: Truck, code: 'logistics' },
]

export default function JobsPage() {
  const [params, setParams] = useSearchParams()
  const [keyword, setKeyword] = useState('')

  const id = params.get('id')
  const category = params.get('category')
  const q = params.get('q')

  if (id) return <JobDetail id={id} />
  if (category || q || params.has('list')) return <JobList category={category} q={q} />

  const search = (e) => {
    e.preventDefault()
    setParams(keyword.trim() ? { q: keyword.trim() } : { list: '1' })
  }

  return (
    <div className="jobs-page">
      <div className="jobs-hero">
        <h1>구인구직</h1>
        <p>
          충남의 다양한 일자리를
          <br />
          한눈에 찾아보세요
        </p>
      </div>

      <form className="jobs-search" onSubmit={search}>
        <Search size={16} aria-hidden="true" />
        <input
          type="text"
          aria-label="일자리 검색"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </form>

      <div className="jobs-quick">
        {QUICK_MENUS.map(({ label, icon: Icon, list }) => (
          <button
            key={label}
            type="button"
            className="jobs-quick-item"
            onClick={list ? () => setParams({ list: '1' }) : undefined}
          >
            <Icon size={22} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      <button type="button" className="jobs-ai">
        <span className="jobs-ai-text">
          <span className="jobs-ai-badge">AI 추천</span>
          <strong>
            내게 맞는 일자리를
            <br />
            추천해드려요!
          </strong>
        </span>
        <ChevronRight size={24} aria-hidden="true" />
      </button>

      <h2 className="jobs-heading">지금 많이 찾는 일자리</h2>
      <div className="jobs-popular">
        {POPULAR_CATEGORIES.map(({ label, icon: Icon, code }) => (
          <button
            key={code}
            type="button"
            className="jobs-popular-item"
            onClick={() => setParams({ category: code })}
          >
            <Icon size={24} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}