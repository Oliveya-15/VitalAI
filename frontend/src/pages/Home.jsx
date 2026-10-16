import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { ArrowRight, Bot, Droplets, Siren, Stethoscope, Wrench, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import ActivityList from '../components/ActivityList'

const CARDS = [
  { to: '/diagnosis', icon: Stethoscope, title: 'AI Diagnosis', text: 'Screen for diabetes, heart disease and Parkinson\'s with ML models, see which factors drive the result.', color: 'text-brand-600', tile: 'bg-brand-50' },
  { to: '/assistant', icon: Bot, title: 'AI Health Assistant', text: 'Ask health questions. An AI agent searches a medical knowledge base and calls our models and tools.', color: 'text-sky-500', tile: 'bg-sky-50' },
  { to: '/blood', icon: Droplets, title: 'Blood Network', text: 'Register as a donor or request blood. Smart matching by blood-group compatibility, distance and eligibility.', color: 'text-red-500', tile: 'bg-red-50' },
  { to: '/emergency', icon: Siren, title: 'Emergency & Ambulance', text: 'Instant emergency triage, nearby hospitals on a map, and an ambulance request tracker.', color: 'text-red-500', tile: 'bg-red-50' },
  { to: '/tools', icon: Wrench, title: 'Health Tools', text: 'BMI, blood-pressure check and a lab-report reader that flags values outside standard ranges.', color: 'text-violet-400', tile: 'bg-violet-50' },
]

export default function Home() {
  const { server } = useOutletContext()
  const { user } = useAuth()
  const [recent, setRecent] = useState(null)
  useEffect(() => { api.activity(4).then(setRecent).catch(() => setRecent([])) }, [])
  const first = user.name.split(' ')[0]

  return (
    <div>
      <section className="rounded-3xl bg-gradient-to-br from-brand-200 via-brand-100 to-sky-50 p-6 text-brand-900 shadow-sm ring-1 ring-brand-200 sm:p-10">
        <p className="text-sm font-semibold text-brand-700">Welcome back, {first} 👋</p>
        <h1 className="mt-1 text-3xl font-extrabold sm:text-4xl">Smarter health decisions, in one place.</h1>
        <p className="mt-3 max-w-2xl text-brand-800">VitalAI combines machine learning, an AI health agent, a community blood-donor network and emergency coordination - built entirely on free, open technology.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to="/diagnosis" className="btn">Start a screening</Link>
          <Link to="/emergency" className="btn-danger"><Siren className="h-4 w-4" /> Emergency help</Link>
        </div>
        {server === 'waking' && <p className="mt-4 text-xs text-brand-700">Connecting to the server - the first load can take up to a minute on the free tier.</p>}
      </section>

      {recent && recent.length > 0 && (
        <div className="card mt-6">
          <div className="flex items-center justify-between">
            <h2 className="font-bold">Pick up where you left off</h2>
            <Link to="/history" className="flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">All activity <ArrowRight className="h-4 w-4" /></Link>
          </div>
          <ActivityList items={recent} />
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {CARDS.map(({ to, icon: Icon, title, text, color, tile }) => (
          <Link key={to} to={to} className="card transition hover:-translate-y-0.5 hover:shadow-md">
            <div className={`inline-flex rounded-xl p-2.5 ${tile}`}><Icon className={`h-6 w-6 ${color}`} /></div>
            <h2 className="mt-3 text-lg font-bold">{title}</h2>
            <p className="mt-1 text-sm text-slate-600">{text}</p>
          </Link>
        ))}
      </div>
      <div className="card mt-6 flex items-start gap-3 text-sm text-slate-600">
        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
        <p>VitalAI provides screening estimates and general information. It does <b>not</b> diagnose, prescribe or replace a doctor. Your screenings and activity are saved to your account and visible only to you.</p>
      </div>
    </div>
  )
}
