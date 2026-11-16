import { MapPin, Clock3, CircleDollarSign, Star } from 'lucide-react'
import { money, payLabel, deadlineLabel } from '../utils/formatters.js'

export default function JobCard({ job, urgent = false, onOpen, onBookmark, busy, bookmarked }) {
  return <article className={urgent ? 'home-urgent-card' : 'home-job-card'}>
    <button className="home-card-open" type="button" onClick={() => onOpen(job.id)}>
      {urgent ? <>
        <span className="home-deadline">{deadlineLabel(job)}</span>
        <h3>{job.title}</h3>
        <p className="home-urgent-description">{job.region?.name} · {job.work_type || job.category?.name}</p>
        <strong className="home-pay"><span>{payLabel(job.pay_type)}</span> {money(job.pay_amount)}원</strong>
      </> : <>
        <span className="home-company">{job.company_name}</span>
        <h3>{job.title}</h3>
        <ul className="home-job-meta">
          <li><MapPin size={14} aria-hidden="true" />{job.address || job.region?.name}</li>
          <li><Clock3 size={14} aria-hidden="true" />{job.start_time?.slice(0, 5)} ~ {job.end_time?.slice(0, 5)}</li>
          <li><CircleDollarSign size={14} aria-hidden="true" />{payLabel(job.pay_type)} {money(job.pay_amount)}원</li>
        </ul>
      </>}
    </button>
    {!urgent && <button className={`home-bookmark${bookmarked ? ' is-saved' : ''}`} type="button" aria-label={`${job.title} 관심 공고`} aria-pressed={bookmarked} disabled={busy} onClick={() => onBookmark(job)}><Star size={23} fill="currentColor" strokeWidth={0} /></button>}
  </article>
}
