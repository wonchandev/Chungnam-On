import { useId } from 'react'

export default function SegmentedControl({ id: controlId, label, value, onChange, options }) {
  const generatedId = useId()
  const id = controlId || generatedId
  return <div className="comm-segments" role="tablist" aria-label={label} onKeyDown={event => {
    const index = options.findIndex(option => option.value === value)
    const next = event.key === 'ArrowRight' ? (index + 1) % options.length : event.key === 'ArrowLeft' ? (index + options.length - 1) % options.length : event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : null
    if (next === null) return
    event.preventDefault()
    onChange(options[next].value)
    event.currentTarget.querySelectorAll('[role="tab"]')[next].focus()
  }}>{options.map(option => <button key={option.value} id={`${id}-${option.value}`} role="tab" type="button" aria-controls={controlId ? `${id}-panel` : undefined} aria-selected={value === option.value} tabIndex={value === option.value ? 0 : -1} onClick={() => onChange(option.value)}>{option.label}</button>)}</div>
}
