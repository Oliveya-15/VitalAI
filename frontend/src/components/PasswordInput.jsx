import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

export default function PasswordInput({ value, onChange, autoComplete = 'current-password', placeholder, id }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input id={id} className="input pr-10" type={show ? 'text' : 'password'} value={value} onChange={onChange}
        autoComplete={autoComplete} placeholder={placeholder} required maxLength={128} />
      <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Hide password' : 'Show password'}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-slate-500 hover:bg-slate-200">
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  )
}

/** Live checklist + strength bar. Rules match the server: 8+ chars, a letter and a number. */
export function PasswordRules({ value }) {
  const rules = [['At least 8 characters', value.length >= 8], ['Contains a letter', /[A-Za-z]/.test(value)], ['Contains a number', /\d/.test(value)]]
  const score = rules.filter(([, ok]) => ok).length + (value.length >= 12 ? 1 : 0)
  const bar = ['bg-slate-200', 'bg-red-400', 'bg-amber-400', 'bg-brand-400', 'bg-brand-600'][score]
  if (!value) return null
  return (
    <div className="mt-2">
      <div className="flex gap-1">{[1, 2, 3, 4].map((i) => <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= score ? bar : 'bg-slate-200'}`} />)}</div>
      <ul className="mt-2 grid gap-0.5 text-xs">{rules.map(([t, ok]) => <li key={t} className={ok ? 'text-brand-700' : 'text-slate-500'}>{ok ? '✓' : '○'} {t}</li>)}</ul>
    </div>
  )
}
