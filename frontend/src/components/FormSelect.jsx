import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import './FormSelect.css'

export default function FormSelect({ label, name, value, onChange, options, error, disabled = false, required = false }) {
  const id = useId()
  const root = useRef(null)
  const trigger = useRef(null)
  const search = useRef({ text: '', time: 0 })
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const selected = options.findIndex(option => option.value === value)
  useEffect(() => {
    if (!open) return
    function outside(event) {
      if (!root.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])
  useEffect(() => {
    if (open) root.current?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
  }, [open, active])

  function choose(index) {
    const option = options[index]
    if (!option) return
    onChange({ target: { name, value: option.value, type: 'select-one' } })
    setOpen(false)
    trigger.current?.focus()
  }
  function keyDown(event) {
    if (event.currentTarget.matches(':disabled')) return
    if (event.key === 'Tab') { setOpen(false); return }
    if (event.key === 'Escape') { event.preventDefault(); setOpen(false); return }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) {
      event.preventDefault()
      if (!open) {
        setActive(event.key === 'End' ? options.length - 1 : Math.max(0, selected))
        setOpen(true)
      } else if (event.key === 'Enter' || event.key === ' ') choose(active)
      else setActive(index => event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : Math.max(0, Math.min(options.length - 1, index + (event.key === 'ArrowDown' ? 1 : -1))))
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      const now = Date.now()
      search.current = { text: (now - search.current.time < 700 ? search.current.text : '') + event.key, time: now }
      const index = options.findIndex(option => option.label.toLowerCase().startsWith(search.current.text.toLowerCase()))
      if (index >= 0) { setActive(index); setOpen(true) }
    }
  }
  return <div className="form-select" ref={root} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <label id={`${id}-label`} htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label>
    <input type="hidden" name={name} value={value} />
    <div className="form-select-control">
      <button ref={trigger} id={id} type="button" role="combobox" className="form-select-trigger" disabled={disabled || !options.length} aria-labelledby={`${id}-label`} aria-haspopup="listbox" aria-expanded={open} aria-controls={`${id}-list`} aria-activedescendant={open ? `${id}-option-${active}` : undefined} aria-required={required} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} onKeyDown={keyDown} onClick={() => { setActive(Math.max(0, selected)); setOpen(!open) }}>
        <span>{options[selected]?.label || '선택해 주세요'}</span><ChevronDown size={18} aria-hidden="true" className={open ? 'is-open' : ''} />
      </button>
      {open && <ul id={`${id}-list`} role="listbox" aria-labelledby={`${id}-label`} className="form-select-options">
        {options.map((option, index) => <li key={option.value} id={`${id}-option-${index}`} role="option" aria-selected={index === selected} data-active={index === active} onPointerMove={() => setActive(index)} onMouseDown={event => event.preventDefault()} onClick={() => choose(index)}>
          <span>{option.label}</span>{index === selected && <Check size={17} aria-hidden="true" />}
        </li>)}
      </ul>}
    </div>
    {error && <span className="form-select-error" id={`${id}-error`}>{error}</span>}
  </div>
}
