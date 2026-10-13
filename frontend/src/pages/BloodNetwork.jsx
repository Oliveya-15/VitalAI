import { useEffect, useState } from 'react'
import { Droplets, Phone, UserPlus, HandHeart, ListChecks, CheckCircle2 } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, Field, LocateButton, PageTitle, RISK_STYLE, Spinner, Tabs } from '../components/ui'

const GROUPS = ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+']
const URG = { critical: 'high', urgent: 'moderate', normal: 'low' }

function Stats() {
  const [s, setS] = useState(null)
  useEffect(() => { api.bloodStats().then(setS).catch(() => {}) }, [])
  if (!s) return null
  return (
    <div className="card mb-5">
      <div className="mb-3 flex gap-6 text-sm"><span><b className="text-xl">{s.total_donors}</b> registered donors</span><span><b className="text-xl text-red-600">{s.open_requests}</b> open requests</span></div>
      <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
        {s.by_group.map((g) => <div key={g.group} className="rounded-xl bg-slate-50 p-2 text-center"><div className="text-sm font-extrabold text-red-600">{g.group}</div><div className="text-[11px] text-slate-500">{g.donors} donors</div>{g.open_requests > 0 && <div className="text-[11px] font-semibold text-red-600">{g.open_requests} need</div>}</div>)}
      </div>
    </div>
  )
}

function DonorForm() {
  const [f, setF] = useState({ name: '', phone: '', blood_group: 'O+', city: '', last_donated: '', consent: false })
  const [pos, setPos] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [done, setDone] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const body = { ...f, ...(pos || {}), last_donated: f.last_donated ? new Date(f.last_donated).toISOString() : null }
      setDone(await api.registerDonor(body))
    } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  if (done) return <div className="card flex items-start gap-3 text-sm"><CheckCircle2 className="h-6 w-6 text-emerald-600" /><div><b>Thank you{done.updated ? ' - profile updated' : ''}!</b><p className="text-slate-600">You may be contacted when a compatible patient nearby needs blood. You can remove yourself anytime from the "Manage" tab.</p></div></div>
  return (
    <form className="card" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name"><input className="input" value={f.name} onChange={set('name')} required minLength={2} /></Field>
        <Field label="Phone number" hint="Shared only with people who post a matching blood request."><input className="input" type="tel" value={f.phone} onChange={set('phone')} required /></Field>
        <Field label="Blood group"><select className="input" value={f.blood_group} onChange={set('blood_group')}>{GROUPS.map((g) => <option key={g}>{g}</option>)}</select></Field>
        <Field label="City"><input className="input" value={f.city} onChange={set('city')} required /></Field>
        <Field label="Last donation date (if any)"><input className="input" type="date" max={new Date().toISOString().slice(0, 10)} value={f.last_donated} onChange={set('last_donated')} /></Field>
        <div className="flex items-end"><LocateButton label={pos ? 'Location saved ✓' : 'Add my location (better matching)'} onLocate={setPos} /></div>
      </div>
      <label className="mt-4 flex items-start gap-2 text-sm text-slate-700"><input type="checkbox" className="mt-1" checked={f.consent} onChange={set('consent')} /> I agree to be contacted by people who need blood, and I confirm I am healthy and eligible to donate.</label>
      <div className="mt-3"><ErrorBox message={err} /></div>
      <button className="btn mt-4" disabled={busy || !f.consent}>{busy && <Spinner />} Register as donor</button>
    </form>
  )
}

function Matches({ matches }) {
  if (!matches.length) return <p className="mt-3 text-sm text-slate-600">No eligible donors found nearby yet. Your request is posted publicly so new donors can respond. Also try the hospital's blood bank and national portals such as eRaktKosh (India).</p>
  return (
    <ul className="mt-3 divide-y divide-slate-100">
      {matches.map((m) => (
        <li key={m.donor_id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
          <div><b>{m.name}</b> <span className="badge bg-red-100 text-red-700">{m.blood_group}</span> {m.exact_match && <span className="badge bg-emerald-100 text-emerald-700">exact match</span>}<div className="text-xs text-slate-500">{m.city}{m.distance_km != null ? ` · ${m.distance_km} km away` : ''}</div></div>
          <a className="btn !py-2" href={`tel:${m.phone}`}><Phone className="h-4 w-4" /> {m.phone}</a>
        </li>
      ))}
    </ul>
  )
}

function RequestForm() {
  const [f, setF] = useState({ patient_name: '', blood_group: 'O+', units: 1, hospital: '', city: '', urgency: 'urgent', contact_phone: '', note: '' })
  const [pos, setPos] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [out, setOut] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { setOut(await api.createBloodRequest({ ...f, units: +f.units, ...(pos || {}) })) } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <div>
      <form className="card" onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Patient name"><input className="input" value={f.patient_name} onChange={set('patient_name')} required /></Field>
          <Field label="Your phone (to be contacted)"><input className="input" type="tel" value={f.contact_phone} onChange={set('contact_phone')} required /></Field>
          <Field label="Blood group needed"><select className="input" value={f.blood_group} onChange={set('blood_group')}>{GROUPS.map((g) => <option key={g}>{g}</option>)}</select></Field>
          <Field label="Units"><input className="input" type="number" min="1" max="10" value={f.units} onChange={set('units')} /></Field>
          <Field label="Hospital"><input className="input" value={f.hospital} onChange={set('hospital')} required /></Field>
          <Field label="City"><input className="input" value={f.city} onChange={set('city')} required /></Field>
          <Field label="Urgency"><select className="input" value={f.urgency} onChange={set('urgency')}><option value="normal">Normal (planned)</option><option value="urgent">Urgent (within 24h)</option><option value="critical">Critical (within hours)</option></select></Field>
          <div className="flex items-end"><LocateButton label={pos ? 'Hospital location saved ✓' : 'Use my current location'} onLocate={setPos} /></div>
        </div>
        <Field label="Note (optional)"><textarea className="input mt-4" rows={2} maxLength={400} value={f.note} onChange={set('note')} /></Field>
        <div className="mt-3"><ErrorBox message={err} /></div>
        <button className="btn mt-4" disabled={busy}>{busy && <Spinner />} Post request & find donors</button>
      </form>
      {out && (
        <div className="card mt-5">
          <h3 className="font-bold">Request #{out.request.id} posted · {out.matches.length} compatible donor(s) found</h3>
          <p className="text-xs text-slate-500">Ranked by exact group match, then distance. Donors are only listed if they have consented and passed the donation rest period.</p>
          <Matches matches={out.matches} />
        </div>
      )}
    </div>
  )
}

function Board() {
  const [rows, setRows] = useState(null), [err, setErr] = useState(''), [city, setCity] = useState(''), [bg, setBg] = useState('')
  const load = () => { setRows(null); api.bloodRequests(`?${new URLSearchParams({ ...(city && { city }), ...(bg && { blood_group: bg }) })}`).then(setRows).catch((e) => setErr(e.message)) }
  useEffect(() => { load() }, [bg]) // eslint-disable-line
  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        <input className="input max-w-[200px]" placeholder="Filter by city" value={city} onChange={(e) => setCity(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} />
        <select className="input max-w-[140px]" value={bg} onChange={(e) => setBg(e.target.value)}><option value="">All groups</option>{GROUPS.map((g) => <option key={g}>{g}</option>)}</select>
        <button className="btn-ghost" onClick={load}>Search</button>
      </div>
      <ErrorBox message={err} />
      {!rows && !err && <p className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> Loading…</p>}
      {rows && rows.length === 0 && <div className="card text-sm text-slate-600">No open requests right now.</div>}
      <div className="grid gap-3 sm:grid-cols-2">
        {rows?.map((r) => (
          <div key={r.id} className="card">
            <div className="flex items-center justify-between"><span className="text-2xl font-extrabold text-red-600">{r.blood_group}</span><span className={`badge ${RISK_STYLE[URG[r.urgency]]}`}>{r.urgency}</span></div>
            <p className="mt-1 text-sm"><b>{r.units}</b> unit(s) · {r.hospital}, {r.city}</p>
            {r.note && <p className="text-xs text-slate-500">{r.note}</p>}
            <a className="btn mt-3 !py-2" href={`tel:${r.contact_phone}`}><HandHeart className="h-4 w-4" /> I can help - call</a>
          </div>
        ))}
      </div>
    </div>
  )
}

function Manage() {
  const [phone, setPhone] = useState(''), [rid, setRid] = useState(''), [msg, setMsg] = useState(''), [err, setErr] = useState('')
  const run = async (fn) => { setErr(''); setMsg(''); try { setMsg(await fn()) } catch (e) { setErr(e.message) } }
  return (
    <div className="card space-y-5">
      <Field label="Your phone number (used to verify it is you)"><input className="input max-w-sm" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} /></Field>
      <div>
        <p className="text-sm font-semibold">Remove me from the donor list</p>
        <button className="btn-ghost mt-2" disabled={!phone} onClick={() => run(async () => { const r = await api.optOut(phone); return r.removed ? 'Your donor record was deleted.' : 'No donor record found for that number.' })}>Delete my donor data</button>
      </div>
      <div>
        <p className="text-sm font-semibold">Close a blood request you created</p>
        <div className="mt-2 flex flex-wrap gap-2"><input className="input max-w-[160px]" placeholder="Request ID" value={rid} onChange={(e) => setRid(e.target.value)} />
          <button className="btn" disabled={!phone || !rid} onClick={() => run(async () => { await api.closeBloodRequest(rid, phone, 'fulfilled'); return `Request #${rid} marked fulfilled.` })}>Mark fulfilled</button>
          <button className="btn-ghost" disabled={!phone || !rid} onClick={() => run(async () => { await api.closeBloodRequest(rid, phone, 'cancelled'); return `Request #${rid} cancelled.` })}>Cancel</button></div>
      </div>
      <ErrorBox message={err} />{msg && <p className="text-sm font-semibold text-emerald-700">{msg}</p>}
    </div>
  )
}

export default function BloodNetwork() {
  const [tab, setTab] = useState('request')
  return (
    <div>
      <PageTitle icon={Droplets} title="Blood Network" subtitle="Community blood donors and requests with smart compatibility matching." />
      <Stats />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: 'request', label: 'Request blood' }, { value: 'donate', label: 'Become a donor' }, { value: 'board', label: 'Open requests' }, { value: 'manage', label: 'Manage' }]} />
      {tab === 'request' && <RequestForm />}
      {tab === 'donate' && <DonorForm />}
      {tab === 'board' && <Board />}
      {tab === 'manage' && <Manage />}
      <p className="mt-4 flex items-start gap-1 text-xs text-slate-500"><ListChecks className="mt-0.5 h-3 w-3 shrink-0" /> Always confirm blood group and cross-matching at a licensed blood bank or hospital. Never pay for blood donation.</p>
    </div>
  )
}
