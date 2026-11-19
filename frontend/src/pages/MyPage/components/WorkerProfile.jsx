import { useCallback, useRef, useState } from 'react'
import { BriefcaseBusiness, Save } from 'lucide-react'
import useAdminResource from '../../Administration/useAdminResource.js'
import ResourceState from './ResourceState.jsx'
import { myRequest, errorText, fieldErrors, fieldError } from '../api.js'

function WorkerForm({ profile, categories, regions }) {
  const [values, setValues] = useState(() => ({ ...profile, experience_years: String(profile.experience_years), weekdays: profile.available_weekdays ? profile.available_weekdays.split(',') : [] }))
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState('')
  const pending = useRef(false)
  function update(name, value) { setValues(current => ({ ...current, [name]: value })); setErrors({}); setNotice('') }
  function toggle(name, value) { setValues(current => ({ ...current, [name]: current[name].includes(value) ? current[name].filter(item => item !== value) : [...current[name], value] })); setErrors({}); setNotice('') }
  async function save(event) {
    event.preventDefault()
    if (pending.current) return
    pending.current = true; setBusy(true); setErrors({}); setNotice('')
    try {
      await myRequest('me/worker-profile/', { method: 'PATCH', body: { experience_years: Number(values.experience_years), experience_note: values.experience_note, available_categories: values.available_categories, available_weekdays: [...values.weekdays].sort().join(','), desired_regions: values.desired_regions, can_night_shift: values.can_night_shift } })
      setNotice('근로자 이력을 저장했어요. 일자리 추천에 반영됩니다.')
    } catch (error) { setErrors({ ...fieldErrors(error), form: errorText(error) }) }
    finally { pending.current = false; setBusy(false) }
  }
  return <form className="my-form" onSubmit={save}><fieldset disabled={busy}>
    <label className="my-field">경력 (년)<input type="number" min="0" step="1" required value={values.experience_years} onChange={event => update('experience_years', event.target.value)} />{errors.experience_years && <span className="my-error">{fieldError(errors, 'experience_years')}</span>}</label>
    <label className="my-field">경력 소개<textarea rows={4} maxLength={500} value={values.experience_note} onChange={event => update('experience_note', event.target.value)} placeholder="해본 일이나 자신 있는 업무를 소개해 주세요." />{errors.experience_note && <span className="my-error">{fieldError(errors, 'experience_note')}</span>}<small>{values.experience_note.length} / 500자</small></label>
    <fieldset className="my-checkbox-group"><legend>가능 업종</legend><div className="my-choice-grid">{categories.map(category => <label key={category.code}><input type="checkbox" checked={values.available_categories.includes(category.code)} onChange={() => toggle('available_categories', category.code)} /><span>{category.name}</span></label>)}</div>{errors.available_categories && <p className="my-error">{fieldError(errors, 'available_categories')}</p>}</fieldset>
    <fieldset className="my-checkbox-group"><legend>일할 수 있는 요일</legend><p className="my-help">선택하지 않으면 모든 요일이 가능한 것으로 저장됩니다.</p><div className="my-weekdays">{['월', '화', '수', '목', '금', '토', '일'].map((day, index) => <label key={day}><input type="checkbox" checked={values.weekdays.includes(String(index))} onChange={() => toggle('weekdays', String(index))} /><span>{day}</span></label>)}</div>{errors.available_weekdays && <p className="my-error">{fieldError(errors, 'available_weekdays')}</p>}</fieldset>
    <fieldset className="my-checkbox-group"><legend>희망 근무지역</legend><div className="my-choice-grid">{regions.map(region => <label key={region.code}><input type="checkbox" checked={values.desired_regions.includes(region.code)} onChange={() => toggle('desired_regions', region.code)} /><span>{region.name}</span></label>)}</div>{errors.desired_regions && <p className="my-error">{fieldError(errors, 'desired_regions')}</p>}</fieldset>
    <label className="my-checkbox-line"><input type="checkbox" checked={values.can_night_shift} onChange={event => update('can_night_shift', event.target.checked)} />야간 근무가 가능해요</label>
    {errors.form && <p className="my-error" role="alert">{errors.form}</p>}{notice && <p className="my-success" role="status">{notice}</p>}
    <button className="my-primary"><Save size={17} />{busy ? '저장 중…' : '이력 저장'}</button>
  </fieldset></form>
}
export default function WorkerProfile({ regions, categories }) {
  const load = useCallback(signal => myRequest('me/worker-profile/', { signal }), [])
  const resource = useAdminResource(load)
  return <section className="my-card"><div className="my-section-heading"><h2><BriefcaseBusiness size={20} />근로자 이력</h2><span>나에게 맞는 일자리의 시작</span></div><p className="my-section-description">경력과 희망 조건을 저장하면 맞춤 일자리 추천에 활용돼요.</p><ResourceState resource={resource}>{data => <WorkerForm profile={data} regions={regions} categories={categories} />}</ResourceState></section>
}
