import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Ambulance, ArrowRight, Droplets, FileText, KeyRound, Mail, MapPin, Phone, Stethoscope, Trash2, UserCircle, LogOut } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import ActivityList from '../components/ActivityList'
import PasswordInput, { PasswordRules } from '../components/PasswordInput'
import { ErrorBox, Field, PageTitle, RISK_STYLE, Spinner, Tabs } from '../components/ui'

const GROUPS = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
export const initials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?'
const fmt = (iso) => new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })

function Stat({ icon: Icon, label, value, tone }) {
  return (
    <div className="card !p-3 sm:!p-4">
      <span className={`inline-flex rounded-xl p-2 ${tone}`}><Icon className="h-5 w-5" /></span>
      <div className="mt-2 text-xl sm:text-2xl font-extrabold truncate">{value}</div>
      <div className="text-xs text-slate-500 truncate">{label}</div>
    </div>
  )
}

function Overview({ summary, activity }) {
  const last = summary?.last_assessment
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={Stethoscope} label="Screenings" value={summary?.assessments ?? '–'} tone="bg-brand-50 text-brand-600" />
        <Stat icon={Droplets} label="Blood requests" value={summary?.blood_requests ?? '–'} tone="bg-red-50 text-red-500" />
        <Stat icon={Ambulance} label="Ambulance requests" value={summary?.ambulance_requests ?? '–'} tone="bg-red-50 text-red-500" />
        <Stat icon={FileText} label="Reports analysed" value={summary?.reports_analysed ?? '–'} tone="bg-violet-50 text-violet-500" />
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        <div className="card lg:col-span-2 overflow-hidden">
          <div className="mb-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
            <h2 className="font-bold">Recent activity</h2>
            <Link to="/history" className="flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">View full history <ArrowRight className="h-4 w-4" /></Link>
          </div>
          {activity === null ? <p className="py-4 text-sm text-slate-500"><Spinner className="inline" /> Loading…</p> : <ActivityList items={activity.slice(0, 8)} empty="Nothing yet - try a screening or ask the assistant a question." />}
        </div>
        <div className="space-y-5">
          <div className="card">
            <h2 className="font-bold">Latest screening</h2>
            {last ? (
              <div className="mt-2 text-sm">
                <p className="capitalize break-words">{last.disease} · {Math.round(last.probability * 100)}%</p>
                <span className={`badge mt-1 ${RISK_STYLE[last.risk_level]}`}>{last.risk_level} risk</span>
                <p className="mt-2 text-xs text-slate-500">{fmt(last.created_at)}</p>
              </div>
            ) : <p className="mt-2 text-sm text-slate-500">No screenings yet.</p>}
            <Link to="/diagnosis" className="btn-ghost mt-3 w-full text-center block">{last ? 'New screening' : 'Start a screening'}</Link>
          </div>
          <div className="card">
            <h2 className="font-bold">Blood donor</h2>
            <p className="mt-1 text-sm text-slate-600">{summary?.donor_registered ? 'You are registered as a donor. Thank you!' : 'You are not registered as a donor yet.'}</p>
            <Link to="/blood" className="btn-ghost mt-3 w-full text-center block">Blood Network</Link>
          </div>
        </div>
      </div>
    </div>
  )
}

function EditProfile() {
  const { user, setUser } = useAuth()
  const [f, setF] = useState({ name: user.name, phone: user.phone || '', city: user.city || '', blood_group: user.blood_group || '' })
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [ok, setOk] = useState(false)
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setOk(false) }
  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr(''); setOk(false)
    try { setUser(await api.updateMe({ name: f.name, phone: f.phone || null, city: f.city || null, blood_group: f.blood_group || null })); setOk(true) }
    catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <form className="card max-w-2xl" onSubmit={save}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name"><input className="input w-full" value={f.name} onChange={set('name')} required minLength={2} maxLength={80} /></Field>
        <Field label="Email" hint="Email cannot be changed."><input className="input opacity-60 w-full" value={user.email} disabled /></Field>
        <Field label="Phone"><input className="input w-full" type="tel" value={f.phone} onChange={set('phone')} /></Field>
        <Field label="City"><input className="input w-full" value={f.city} onChange={set('city')} /></Field>
        <Field label="Blood group"><select className="input w-full" value={f.blood_group} onChange={set('blood_group')}><option value="">Not set</option>{GROUPS.map((g) => <option key={g}>{g}</option>)}</select></Field>
      </div>
      <div className="mt-3"><ErrorBox message={err} /></div>
      {ok && <p className="mt-3 text-sm font-semibold text-brand-700">Profile saved.</p>}
      <button className="btn mt-4 w-full sm:w-auto" disabled={busy}>{busy && <Spinner />} Save changes</button>
    </form>
  )
}

function Security() {
  const { logout } = useAuth()
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' })
  const [busy, setBusy] = useState(false), [err, setErr] = useState(''), [ok, setOk] = useState(false)
  const [delPw, setDelPw] = useState(''), [delBusy, setDelBusy] = useState(false), [delErr, setDelErr] = useState('')

  const change = async (e) => {
    e.preventDefault(); setErr(''); setOk(false)
    if (pw.next !== pw.confirm) return setErr('New passwords do not match.')
    setBusy(true)
    try { await api.changePassword({ current_password: pw.current, new_password: pw.next }); setOk(true); setPw({ current: '', next: '', confirm: '' }) }
    catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  const remove = async (e) => {
    e.preventDefault()
    if (!confirm('Permanently delete your account and all data created with it? This cannot be undone.')) return
    setDelBusy(true); setDelErr('')
    try { await api.deleteAccount(delPw); logout('Your account was deleted.') } catch (x) { setDelErr(x.message); setDelBusy(false) }
  }
  return (
    <div className="grid max-w-4xl gap-5 lg:grid-cols-2">
      <form className="card space-y-4" onSubmit={change}>
        <h2 className="flex items-center gap-2 font-bold"><KeyRound className="h-5 w-5 text-brand-600 shrink-0" /> Change password</h2>
        <Field label="Current password"><PasswordInput value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} /></Field>
        <div><Field label="New password"><PasswordInput value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} autoComplete="new-password" /></Field><PasswordRules value={pw.next} /></div>
        <Field label="Confirm new password"><PasswordInput value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} autoComplete="new-password" /></Field>
        <ErrorBox message={err} />{ok && <p className="text-sm font-semibold text-brand-700">Password updated.</p>}
        <button className="btn w-full sm:w-auto" disabled={busy}>{busy && <Spinner />} Update password</button>
      </form>
      <form className="card space-y-4 !bg-red-50/60 ring-red-100" onSubmit={remove}>
        <h2 className="flex items-center gap-2 font-bold text-red-700"><Trash2 className="h-5 w-5 shrink-0" /> Delete account</h2>
        <p className="text-sm text-slate-600">Permanently removes your account, screening history, activity, blood requests, donor profile and ambulance records created through it.</p>
        <Field label="Confirm with your password"><PasswordInput value={delPw} onChange={(e) => setDelPw(e.target.value)} /></Field>
        <ErrorBox message={delErr} />
        <button className="btn-danger w-full sm:w-auto" disabled={delBusy || !delPw}>{delBusy && <Spinner />} Delete my account</button>
      </form>
    </div>
  )
}

export default function Profile() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState('overview')
  const [summary, setSummary] = useState(null), [activity, setActivity] = useState(null), [error, setError] = useState('')
  useEffect(() => {
    api.summary().then(setSummary).catch((e) => setError(e.message))
    api.activity(20).then(setActivity).catch(() => setActivity([]))
  }, [])

  return (
    <div className="w-full max-w-full overflow-x-hidden pb-10">
      <PageTitle icon={UserCircle} title="My Profile" />
      <div className="card mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-300 to-brand-500 text-xl font-extrabold text-white">{initials(user.name)}</div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-xl font-extrabold">{user.name}</h2>
            <div className="mt-1 flex flex-col sm:flex-row sm:flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
              <span className="flex items-center gap-1 truncate"><Mail className="h-4 w-4 shrink-0" /> <span className="truncate">{user.email}</span></span>
              {user.phone && <span className="flex items-center gap-1"><Phone className="h-4 w-4 shrink-0" /> {user.phone}</span>}
              {user.city && <span className="flex items-center gap-1"><MapPin className="h-4 w-4 shrink-0" /> {user.city}</span>}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              {user.blood_group && <span className="badge bg-red-100 text-red-700">Blood group {user.blood_group}</span>}
              <span className="text-slate-500">Member since {fmt(user.created_at)}</span>
            </div>
          </div>
        </div>
        <button className="btn-ghost shrink-0 w-full sm:w-auto justify-center" onClick={() => logout()}><LogOut className="h-4 w-4" /> Sign out</button>
      </div>
      <ErrorBox message={error} />
      <div className="overflow-x-auto pb-2">
        <Tabs value={tab} onChange={setTab} tabs={[{ value: 'overview', label: 'Overview' }, { value: 'edit', label: 'Edit profile' }, { value: 'security', label: 'Security' }]} />
      </div>
      <div className="mt-4">
        {tab === 'overview' && <Overview summary={summary} activity={activity} />}
        {tab === 'edit' && <EditProfile />}
        {tab === 'security' && <Security />}
      </div>
    </div>
  )
}