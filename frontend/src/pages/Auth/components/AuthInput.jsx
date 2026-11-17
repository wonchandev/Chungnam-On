import { useId, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

export default function AuthInput({ label, error, type = 'text', ...props }) {
  const id = useId()
  const [visible, setVisible] = useState(false)
  const password = type === 'password'
  return <div className="auth-field">
    <label htmlFor={id}>{label}</label>
    <div className={password ? 'auth-password-control' : undefined}>
      <input {...props} type={password && visible ? 'text' : type} id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : undefined} />
      {password && <button className="auth-password-toggle" type="button" aria-label={`${label} ${visible ? '숨기기' : '보기'}`} aria-controls={id} aria-pressed={visible} onClick={() => setVisible(current => !current)}>
        {visible ? <EyeOff size={20} aria-hidden="true" /> : <Eye size={20} aria-hidden="true" />}
      </button>}
    </div>
    {error && <span className="auth-error" id={`${id}-error`}>{error}</span>}
  </div>
}
