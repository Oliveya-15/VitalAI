import { useEffect, useState } from 'react'
import { Link, NavLink, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Bot, Droplets, History as HistoryIcon, Home as HomeIcon, LogOut, Siren, Stethoscope, Wrench, Menu, X, UserCircle } from 'lucide-react'
import { api } from './services/api'
import { useAuth } from './context/AuthContext'
import ProtectedRoute, { PublicOnly } from './components/ProtectedRoute'
import Home from './pages/Home'
import Diagnosis from './pages/Diagnosis'
import Assistant from './pages/Assistant'
import BloodNetwork from './pages/BloodNetwork'
import Emergency from './pages/Emergency'
import Tools from './pages/Tools'
import History from './pages/History'
import Profile, { initials } from './pages/Profile'
import Login from './pages/Login'
import Register from './pages/Register'

const NAV = [
  { to: '/', label: 'Home', icon: HomeIcon, end: true },
  { to: '/diagnosis', label: 'Diagnosis', icon: Stethoscope },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/blood', label: 'Blood Network', icon: Droplets },
  { to: '/emergency', label: 'Emergency', icon: Siren },
  { to: '/tools', label: 'Health Tools', icon: Wrench },
  { to: '/history', label: 'My History', icon: HistoryIcon },
  { to: '/profile', label: 'My Profile', icon: UserCircle },
]

// Logo from frontend/public/logo.png. If your logo image already contains the "VitalAI" name,
// set SHOW_NAME to false so the name is not shown twice.
const SHOW_NAME = false

function Brand({ size = 'h-9' }) {
  return (
    <div className="flex items-center gap-2">
      <img src="/logo.png" alt="VitalAI logo" className={`${size} w-auto object-contain`} />
    </div>
  )
}

function Avatar({ name, size = 'h-9 w-9 text-sm' }) {
  return <div className={`flex ${size} shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-300 to-brand-500 font-extrabold text-white`}>{initials(name)}</div>
}

/** Signed-in layout: sidebar + page area. Pages render through <Outlet />. */
function Shell({ server }) {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen lg:flex">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 transform flex-col overflow-y-auto bg-white p-4 ring-1 ring-slate-200 transition lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
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
        <div className="mt-auto pt-6">
          <div className="mb-3 rounded-xl bg-brand-50 p-3 text-xs text-slate-600">
            <span className={`mr-1 inline-block h-2 w-2 rounded-full ${server === 'up' ? 'bg-emerald-500' : server === 'down' ? 'bg-red-400' : 'animate-pulse bg-amber-400'}`} />
            {server === 'up' ? 'Server online' : server === 'down' ? 'Server unreachable' : 'Waking server… (up to 1 min on first visit)'}
          </div>
          <div className="flex items-center gap-2 rounded-xl p-2 ring-1 ring-slate-200">
            <Link to="/profile" onClick={() => setOpen(false)} className="flex min-w-0 flex-1 items-center gap-2">
              <Avatar name={user.name} />
              <span className="min-w-0"><span className="block truncate text-sm font-semibold">{user.name}</span><span className="block truncate text-[11px] text-slate-500">{user.email}</span></span>
            </Link>
            <button onClick={() => logout()} title="Sign out" aria-label="Sign out" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-red-500"><LogOut className="h-4 w-4" /></button>
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-slate-500">Not a medical device. Information only - always consult a doctor. In an emergency call your local ambulance number.</p>
        </div>
      </aside>
      {open && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />}
      <main className="min-w-0 flex-1">
        <header className="flex items-center justify-between gap-3 bg-white px-4 py-3 ring-1 ring-slate-200 lg:hidden">
          <div className="flex items-center gap-3">
            <button onClick={() => setOpen(true)} aria-label="Open menu"><Menu /></button>
            <Brand size="h-8" />
          </div>
          <Link to="/profile" aria-label="My profile"><Avatar name={user.name} size="h-8 w-8 text-xs" /></Link>
        </header>
        <div className="mx-auto max-w-5xl p-4 sm:p-6 lg:p-8">
          <Outlet context={{ server }} />
        </div>
      </main>
    </div>
  )
}

export default function App() {
  const [server, setServer] = useState('waking') // waking | up | down

  // Wake the free-tier backend as soon as the site opens (even on the login page),
  // then keep it warm while the tab is open.
  useEffect(() => {
    let alive = true
    const ping = () => api.ping().then(() => alive && setServer('up')).catch(() => alive && setServer('down'))
    ping()
    const id = setInterval(ping, 10 * 60 * 1000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  return (
    <Routes>
      <Route path="/login" element={<PublicOnly><Login server={server} /></PublicOnly>} />
      <Route path="/register" element={<PublicOnly><Register server={server} /></PublicOnly>} />
      <Route element={<ProtectedRoute><Shell server={server} /></ProtectedRoute>}>
        <Route path="/" element={<Home />} />
        <Route path="/diagnosis" element={<Diagnosis />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/blood" element={<BloodNetwork />} />
        <Route path="/emergency" element={<Emergency />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/history" element={<History />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
