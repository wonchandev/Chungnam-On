import { Building2, Package } from 'lucide-react'
import { money, payLabel } from '../utils/formatters.js'
import ResourceState from './ResourceState.jsx'

export default function JobTicker({ resource, onLogin, onOpen }) {
  return (
    <div className="home-ticker" aria-label="새로 올라온 일자리">
      <ResourceState resource={resource} onLogin={onLogin} empty="새로 올라온 일자리를 기다리고 있어요.">{(jobs) => jobs.slice(0, 3).map((job) => {
        const Icon = job.category === 'logistics' || job.category?.code === 'logistics' ? Package : Building2
        return <button className="home-ticker-item" type="button" key={job.id} onClick={() => onOpen(job.id)}>
          <span><strong>{job.label || `[${payLabel(job.pay_type)} ${money(job.pay_amount)}] ${job.title}`}</strong><span className="home-ticker-pay"><span>{payLabel(job.pay_type)}</span> {money(job.pay_amount)}원</span></span>
          <Icon size={29} strokeWidth={2.3} aria-hidden="true" />
        </button>
      })}</ResourceState>
    </div>
  )
}
