import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown, MapPin } from 'lucide-react'
import './RegionPicker.css'

export default function RegionPicker({ value, regions, onChange, loading = false }) {
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const [panel, setPanel] = useState({ placement: 'bottom', height: 480 })
  const containerRef = useRef(null)
  const triggerRef = useRef(null)
  const listRef = useRef(null)
  const listId = useId()
  const options = [{ code: '', name: '충남 전체' }, ...regions]
  const selectedIndex = Math.max(0, options.findIndex((region) => region.code === value))
  const selected = options[selectedIndex]

  useEffect(() => {
    if (!open) return
    listRef.current?.focus()
    function closeOutside(event) {
      if (!containerRef.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', closeOutside)
    const closeOnResize = () => setOpen(false)
    window.addEventListener('resize', closeOnResize)
    return () => {
      document.removeEventListener('pointerdown', closeOutside)
      window.removeEventListener('resize', closeOnResize)
    }
  }, [open])

  useEffect(() => {
    if (open) document.getElementById(`${listId}-${activeIndex}`)?.scrollIntoView({ block: 'nearest' })
  }, [open, activeIndex, listId])

  function showOptions(index = selectedIndex) {
    const rect = triggerRef.current.getBoundingClientRect()
    const below = window.innerHeight - rect.bottom - 24
    const above = rect.top - 24
    const placement = below < 300 && above > below ? 'top' : 'bottom'
    setPanel({ placement, height: Math.max(160, placement === 'top' ? above : below) })
    setActiveIndex(index)
    setOpen(true)
  }

  function choose(index) {
    onChange(options[index].code)
    setOpen(false)
    triggerRef.current?.focus()
  }

  function handleKeyDown(event) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        setActiveIndex((index) => (index + 1) % options.length)
        break
      case 'ArrowUp':
        event.preventDefault()
        setActiveIndex((index) => (index - 1 + options.length) % options.length)
        break
      case 'Home':
        event.preventDefault()
        setActiveIndex(0)
        break
      case 'End':
        event.preventDefault()
        setActiveIndex(options.length - 1)
        break
      case 'Enter':
      case ' ':
        event.preventDefault()
        choose(activeIndex)
        break
      case 'Escape':
        event.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
        break
      case 'Tab':
        setOpen(false)
        break
      default:
        break
    }
  }

  return (
    <div className="region-picker" ref={containerRef} onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false)
    }}>
      <button
        ref={triggerRef}
        className={`region-picker-trigger${open ? ' is-open' : ''}`}
        type="button"
        aria-label={`일자리를 찾을 지역: ${selected.name}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => open ? setOpen(false) : showOptions()}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault()
            showOptions(event.key === 'ArrowUp' ? options.length - 1 : selectedIndex)
          }
        }}
      >
        <span className="region-picker-pin"><MapPin size={17} aria-hidden="true" /></span>
        <span>{selected.name}</span>
        <ChevronDown className="region-picker-chevron" size={16} aria-hidden="true" />
      </button>

      {open && (
        <div className="region-picker-panel" data-placement={panel.placement} style={{ '--region-picker-height': `${panel.height}px` }}>
          <div className="region-picker-heading">
            <span className="region-picker-eyebrow">충청남도</span>
            <strong>어디에서 일할까요?</strong>
            <p>원하는 지역의 일자리를 찾아보세요.</p>
          </div>
          <div
            ref={listRef}
            id={listId}
            className="region-picker-list"
            role="listbox"
            aria-label="일자리를 찾을 지역"
            aria-activedescendant={`${listId}-${activeIndex}`}
            aria-busy={loading}
            tabIndex={0}
            onKeyDown={handleKeyDown}
          >
            {options.map((region, index) => (
              <div
                key={region.code}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={value === region.code}
                className={`region-picker-option${index === 0 ? ' region-picker-all' : ''}${value === region.code ? ' is-selected' : ''}${activeIndex === index ? ' is-active' : ''}`}
                onPointerMove={() => setActiveIndex(index)}
                onClick={() => choose(index)}
              >
                {index === 0 && <MapPin size={16} aria-hidden="true" />}
                <span>{region.name}</span>
                {value === region.code && <Check size={16} strokeWidth={2.5} aria-hidden="true" />}
              </div>
            ))}
          </div>
          <div className="region-picker-footer">{loading ? '지역 목록을 불러오고 있어요…' : '선택한 지역의 일자리를 보여드려요.'}</div>
        </div>
      )}
    </div>
  )
}
