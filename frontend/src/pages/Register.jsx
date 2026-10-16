import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import AuthLayout from '../components/AuthLayout'
import PasswordInput, { PasswordRules } from '../components/PasswordInput'
import { ErrorBox, Field, Spinner } from '../components/ui'

export default function Register({ server }) {
  const { register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ name: '', email: '', phone: '', password: '', confirm: '', agree: false })
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const submit = async (e) => {
    e.preventDefault(); setError('')
    if (f.password !== f.confirm) return setError('Passwords do not match.')
    if (f.password.length < 8 || !/[A-Za-z]/.test(f.password) || !/\d/.test(f.password)) return setError('Password needs 8+ characters with at least one letter and one number.')
    setBusy(true)
    try {
      await register({ name: f.name, email: f.email, password: f.password, ...(f.phone.trim() ? { phone: f.phone } : {}) })
      nav('/', { replace: true })
    } catch (err) { setError(err.message); setBusy(false) }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Free forever. Your health activity stays private to your account." server={server}>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Full name"><input className="input" autoComplete="name" value={f.name} onChange={set('name')} required minLength={2} maxLength={80} /></Field>
        <Field label="Email"><input className="input" type="email" autoComplete="email" value={f.email} onChange={set('email')} required /></Field>
        <Field label="Phone (optional)" hint="Used to pre-fill blood and ambulance forms. Never shown publicly."><input className="input" type="tel" autoComplete="tel" value={f.phone} onChange={set('phone')} /></Field>
        <div>
          <Field label="Password"><PasswordInput value={f.password} onChange={set('password')} autoComplete="new-password" /></Field>
          <PasswordRules value={f.password} />
        </div>
        <Field label="Confirm password"><PasswordInput value={f.confirm} onChange={set('confirm')} autoComplete="new-password" /></Field>
        <label className="flex items-start gap-2 text-xs text-slate-600"><input type="checkbox" className="mt-0.5" checked={f.agree} onChange={set('agree')} />I understand VitalAI gives screening estimates and general information only. It is not a medical device and does not replace a doctor.</label>
        <ErrorBox message={error} />
        <button className="btn w-full" disabled={busy || !f.agree}>{busy ? <Spinner /> : <UserPlus className="h-4 w-4" />} Create account</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">Already have an account? <Link to="/login" className="font-semibold text-brand-700 hover:underline">Sign in</Link></p>
    </AuthLayout>
  )
}
