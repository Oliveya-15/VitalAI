import { useEffect, useState } from 'react'
import { Phone, ShieldCheck, Stethoscope, Bot, Droplets, Siren } from 'lucide-react'
import { api } from '../services/api'

const POINTS = [
  [Stethoscope, 'ML screening for diabetes, heart disease and Parkinson\'s'],
  [Bot, 'AI health assistant with a built-in medical knowledge base'],
  [Droplets, 'Blood donor network with smart compatibility matching'],
  [Siren, 'Emergency triage, nearby hospitals and ambulance requests'],
]

/** Split-screen shell shared by Login and Register. Emergency numbers stay reachable WITHOUT signing in. */
export default function AuthLayout({ title, subtitle, server, children }) {
  const [nums, setNums] = useState({ ambulance: '108', national_emergency: '112' })
  useEffect(() => { api.numbers().then(setNums).catch(() => { }) }, [])
  return (
    <div className="min-h-screen bg-mint lg:grid lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-gradient-to-br from-brand-200 via-brand-100 to-sky-50 p-10 lg:flex">
        <div className="flex items-center gap-2"><img src="/logo.png" alt="VitalAI" className="h-10 w-auto object-contain" /></div>
        <div>
          <h2 className="text-3xl font-extrabold leading-tight text-brand-900">Smarter health decisions,<br />in one place.</h2>
          <ul className="mt-6 space-y-3">
            {POINTS.map(([Icon, t]) => <li key={t} className="flex items-start gap-3 text-sm text-brand-900"><span className="rounded-lg bg-white/70 p-1.5"><Icon className="h-4 w-4 text-brand-700" /></span>{t}</li>)}
          </ul>
        </div>
        <p className="flex items-start gap-2 text-xs text-brand-800"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" /> Not a medical device. Screening estimates and general information only - always consult a doctor.</p>
      </aside>
      <main className="flex flex-col justify-center p-5 sm:p-10">
        <div className="mx-auto w-full max-w-md">
          {/* Small-screen hero: desktop users get the full split-screen panel instead */}
          <section className="mb-6 rounded-3xl bg-gradient-to-br from-brand-200 via-brand-100 to-sky-50 p-5 text-brand-900 shadow-sm ring-1 ring-brand-200 lg:hidden">
            <img src="/logo.png" alt="VitalAI" className="h-9 w-auto object-contain" />
            <h2 className="mt-3 text-xl font-extrabold leading-tight text-brand-900">Smarter health decisions, in one place.</h2>
            <ul className="mt-4 grid gap-2.5 sm:grid-cols-2">
              {POINTS.map(([Icon, t]) => (
                <li key={t} className="flex items-start gap-2 text-xs text-brand-900">
                  <span className="rounded-lg bg-white/70 p-1.5"><Icon className="h-3.5 w-3.5 text-brand-700" /></span>
                  <span className="pt-0.5 leading-snug">{t}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 flex items-start gap-2 text-xs leading-snug text-brand-800"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" /> Not a medical device. Screening estimates and general information only - always consult a doctor.</p>
          </section>
          <h1 className="text-2xl font-extrabold">{title}</h1>
          <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
          {server === 'waking' && <p className="mt-3 rounded-xl bg-brand-50 p-2.5 text-xs text-brand-800">Waking up the server - the first sign-in can take up to a minute.</p>}
          <div className="card mt-5">{children}</div>
          <div className="mt-5 rounded-2xl bg-red-50 p-3 text-center ring-1 ring-red-100">
            <p className="text-xs font-semibold text-red-700">In an emergency, don't sign in - call now</p>
            <div className="mt-2 flex justify-center gap-2">
              <a href={`tel:${nums.ambulance}`} className="btn-danger !py-2"><Phone className="h-4 w-4" /> Ambulance {nums.ambulance}</a>
              <a href={`tel:${nums.national_emergency}`} className="btn-danger !py-2"><Phone className="h-4 w-4" /> Emergency {nums.national_emergency}</a>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}