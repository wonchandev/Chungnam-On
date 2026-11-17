import { useCallback, useState } from 'react'
import { ArrowRight, GraduationCap } from 'lucide-react'
import useHomeResource from '../../Home/hooks/useHomeResource.js'
import HomeDialog from '../../Home/components/HomeDialog.jsx'
import { communicationRequest, errorMessage } from '../api.js'
import LoadState from './LoadState.jsx'

export default function CourseCards({ session, onLogin }) {
  const [selected, setSelected] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const load = useCallback(signal => communicationRequest('courses/', { signal }), [ ])
  const courses = useHomeResource(load)
  async function enroll() {
    if (!session) { onLogin(); return }
    if (busy) return
    setBusy(true); setNotice('')
    try {
      const course = await communicationRequest(`courses/${selected.id}/enroll/`, { method: selected.is_enrolled ? 'DELETE' : 'POST' })
      setSelected(course); courses.retry()
      setNotice(course.is_enrolled ? '교육 신청이 완료되었어요.' : '교육 신청을 취소했어요.')
    } catch (error) { setNotice(errorMessage(error)) }
    finally { setBusy(false) }
  }
  return <>
    <div className="comm-section-heading"><h2>함께 배우는 언어</h2><span>언어 교육</span></div>
    <LoadState resource={courses} empty="준비된 교육이 없어요.">{data => <div className="comm-courses">{data.map(course => <button className="comm-course" key={course.id} onClick={() => { setSelected(course); setNotice('') }}>
      <span className="comm-course-icon"><GraduationCap size={26} aria-hidden="true" /></span>
      <strong>{course.title}</strong><span className="comm-course-description">{course.description}</span>
      <span className="comm-course-cta">{course.is_enrolled ? '신청 완료' : course.is_free ? '무료로 배우기' : '자세히 보기'}<ArrowRight size={15} /></span>
    </button>)}</div>}</LoadState>
    {selected && <HomeDialog title={selected.title} onClose={() => setSelected(null)}>
      <div className="comm-dialog-content"><p>{selected.description}</p><p>{selected.is_free ? '무료 교육' : '유료 교육'} · {selected.kind === 'video_call' ? '화상 수업' : '강의'}</p>
        <p>신청 {selected.enrolled_count}명{selected.capacity != null ? ` / 정원 ${selected.capacity}명` : ''}</p>
        {notice && <p role="status">{notice}</p>}
        <button className="comm-primary" disabled={busy || (!selected.is_enrolled && selected.capacity != null && selected.enrolled_count >= selected.capacity)} onClick={enroll}>{busy ? '처리 중…' : selected.is_enrolled ? '신청 취소' : selected.capacity != null && selected.enrolled_count >= selected.capacity ? '정원 마감' : '교육 신청하기'}</button>
      </div>
    </HomeDialog>}
  </>
}
