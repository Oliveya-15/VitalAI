import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import AuthLayout from '../components/AuthLayout'
import PasswordInput from '../components/PasswordInput'
import { ErrorBox, Field, Spinner } from '../components/ui'

export default function Login({ server }) {
  const { login, notice } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [email, setEmail] = useState(''), [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try { await login(email, password); nav(loc.state?.from || '/', { replace: true }) }
    catch (err) { setError(err.message); setBusy(false) }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to continue to your VitalAI dashboard." server={server}>
      <form onSubmit={submit} className="space-y-4">
        {notice && <p className="rounded-xl bg-amber-50 p-2.5 text-xs text-amber-800">{notice}</p>}
        <Field label="Email"><input className="input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
        <Field label="Password"><PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
        <ErrorBox message={error} />
        <button className="btn w-full" disabled={busy}>{busy ? <Spinner /> : <LogIn className="h-4 w-4" />} Sign in</button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-600">New to VitalAI? <Link to="/register" className="font-semibold text-brand-700 hover:underline">Create an account</Link></p>
    </AuthLayout>
  )
}
