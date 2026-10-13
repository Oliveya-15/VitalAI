import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Bot, Droplets, History as HistoryIcon, Home as HomeIcon, Siren, Stethoscope, Wrench, Menu, X } from 'lucide-react'
import { api } from './services/api'
import Home from './pages/Home'
import Diagnosis from './pages/Diagnosis'
import Assistant from './pages/Assistant'
import BloodNetwork from './pages/BloodNetwork'
import Emergency from './pages/Emergency'
import Tools from './pages/Tools'
import History from './pages/History'

const NAV = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/diagnosis', label: 'Diagnosis', icon: Stethoscope },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/blood', label: 'Blood Network', icon: Droplets },
  { to: '/emergency', label: 'Emergency', icon: Siren },
  { to: '/tools', label: 'Health Tools', icon: Wrench },
  { to: '/history', label: 'My History', icon: HistoryIcon },
]

// Logo from frontend/public/logo.png. If your logo image already contains the "VitalAI" name,
// set SHOW_NAME to false so the name is not shown twice.
const SHOW_NAME = true

function Brand({ size = 'h-9' }) {
  return (
    <div className="flex items-center gap-2">
      <img src="/logo.png" alt="VitalAI logo" className={`${size} w-auto object-contain`} />
    </div>
  )
}

export default function App() {
  const [open, setOpen] = useState(false)
  const [server, setServer] = useState('waking') // waking | up | down

  // Wake the free-tier backend as soon as the site opens, then keep it warm while the tab is open.
  useEffect(() => {
    let alive = true
    const ping = () => api.ping().then(() => alive && setServer('up')).catch(() => alive && setServer('down'))
    ping()
    const id = setInterval(ping, 10 * 60 * 1000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  return (
    <div className="min-h-screen lg:flex">
      <aside className={`fixed inset-y-0 left-0 z-40 w-64 transform bg-white p-4 ring-1 ring-slate-200 transition lg:static lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-6 flex items-center justify-between">
          <Brand />
          <button className="lg:hidden" onClick={() => setOpen(false)} aria-label="Close menu"><X /></button>
        </div>
        <nav className="space-y-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-600 hover:bg-slate-100'} ${to === '/emergency' && !isActive ? 'text-red-500' : ''}`}>
              <Icon className="h-5 w-5" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-8 rounded-xl bg-brand-50 p-3 text-xs text-slate-600">
          <span className={`mr-1 inline-block h-2 w-2 rounded-full ${server === 'up' ? 'bg-emerald-500' : server === 'down' ? 'bg-red-400' : 'animate-pulse bg-amber-400'}`} />
          {server === 'up' ? 'Server online' : server === 'down' ? 'Server unreachable' : 'Waking server… (up to 1 min on first visit)'}
        </div>
        <p className="mt-4 text-[11px] leading-relaxed text-slate-500">Not a medical device. Information only - always consult a doctor. In an emergency call your local ambulance number.</p>
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />}
      <main className="min-w-0 flex-1">
        <header className="flex items-center gap-3 bg-white px-4 py-3 ring-1 ring-slate-200 lg:hidden">
          <button onClick={() => setOpen(true)} aria-label="Open menu"><Menu /></button>
          <Brand size="h-8" />
        </header>
        <div className="mx-auto max-w-5xl p-4 sm:p-6 lg:p-8">
          <Routes>
            <Route path="/" element={<Home server={server} />} />
            <Route path="/diagnosis" element={<Diagnosis />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/blood" element={<BloodNetwork />} />
            <Route path="/emergency" element={<Emergency />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/history" element={<History />} />
            <Route path="*" element={<Home server={server} />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}