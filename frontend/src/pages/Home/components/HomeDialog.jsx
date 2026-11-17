import { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'

export default function HomeDialog({ title, onClose, children, wide = false, className = '' }) {
  const ref = useRef(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    const previous = document.activeElement
    dialog.showModal()
    return () => { dialog.close(); previous?.focus() }
  }, [])
  return <dialog ref={ref} aria-labelledby={titleId} className={`home-dialog${wide ? ' home-detail-dialog' : ''} ${className}`} onCancel={onClose} onClick={(event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    if (event.target === event.currentTarget && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) onClose()
  }}>
    <div className="home-dialog-heading"><h2 id={titleId}>{title}</h2><button type="button" onClick={onClose} aria-label="닫기"><X size={22} /></button></div>
    {children}
  </dialog>
}
