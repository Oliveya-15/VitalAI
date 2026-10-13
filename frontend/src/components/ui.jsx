import { useState } from 'react'
import { AlertTriangle, Loader2, MapPin } from 'lucide-react'

export const Spinner = ({ className = '' }) => <Loader2 className={`h-4 w-4 animate-spin ${className}`} />

export function PageTitle({ icon: Icon, title, subtitle }) {
  return (
    <div className="mb-6">
      <h1 className="flex items-center gap-2 text-2xl font-extrabold sm:text-3xl">{Icon && <Icon className="h-7 w-7 text-brand-600" />} {title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
    </div>
  )
}

export function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div className="flex items-start gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700 ring-1 ring-red-200">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> <span>{message}</span>
    </div>
  )
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-slate-500">{hint}</span>}
    </label>
  )
}

export const RISK_STYLE = {
  low: 'bg-emerald-100 text-emerald-700',
  moderate: 'bg-amber-100 text-amber-700',
  high: 'bg-red-100 text-red-700',
  emergency: 'bg-red-100 text-red-700',
  urgent: 'bg-amber-100 text-amber-700',
  routine: 'bg-emerald-100 text-emerald-700',
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-5 flex flex-wrap gap-2">
      {tabs.map((t) => (
        <button key={t.value} onClick={() => onChange(t.value)}
          className={`rounded-full px-4 py-2 text-sm font-semibold transition ${value === t.value ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-300 hover:bg-slate-50'}`}>
          {t.label}
        </button>
      ))}
    </div>
  )
}

/** Asks the browser for the user's location (only when they click). */
export function LocateButton({ onLocate, label = 'Use my location' }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const go = () => {
    if (!navigator.geolocation) return setErr('Location is not supported on this device.')
    setBusy(true); setErr('')
    navigator.geolocation.getCurrentPosition(
      (p) => { setBusy(false); onLocate({ lat: +p.coords.latitude.toFixed(5), lon: +p.coords.longitude.toFixed(5) }) },
      () => { setBusy(false); setErr('Could not get location - allow location access or enter details manually.') },
      { enableHighAccuracy: true, timeout: 12000 },
    )
  }
  return (
    <div>
      <button type="button" className="btn-ghost" onClick={go} disabled={busy}>{busy ? <Spinner /> : <MapPin className="h-4 w-4" />} {label}</button>
      {err && <p className="mt-1 text-xs text-red-600">{err}</p>}
    </div>
  )
}

export function Disclaimer({ children }) {
  return <p className="mt-3 text-xs text-slate-500">{children}</p>
}
