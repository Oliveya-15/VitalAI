import { useEffect, useState } from 'react'
import { Siren, Phone, Hospital, Ambulance as AmbIcon, AlertOctagon, Search } from 'lucide-react'
import { api } from '../services/api'
import MapView from '../components/MapView'
import { ErrorBox, Field, LocateButton, PageTitle, RISK_STYLE, Spinner, Tabs } from '../components/ui'

// Free Google Maps directions link: no API key needed. Origin is left out on purpose,
// so Google Maps uses the user's current location.
const googleDirections = (lat, lon) =>
  `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&travelmode=driving`

function Numbers({ n }) {
  if (!n) return null
  const items = [['Ambulance', n.ambulance], ['National emergency', n.national_emergency], ['Ambulance (alt.)', n.ambulance_alt], ['Women helpline', n.women_helpline]]
  return (
    <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {items.map(([l, v]) => <a key={l} href={`tel:${v}`} className="rounded-2xl bg-red-600 p-3 text-center text-white shadow-sm transition hover:bg-red-700"><div className="text-2xl font-extrabold">{v}</div><div className="text-xs opacity-90">{l}</div></a>)}
    </div>
  )
}

function Triage() {
  const [text, setText] = useState(''), [out, setOut] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState('')
  const go = async (e) => { e.preventDefault(); setBusy(true); setErr(''); try { setOut(await api.triage(text)) } catch (x) { setErr(x.message) } finally { setBusy(false) } }
  return (
    <div>
      <form className="card" onSubmit={go}>
        <Field label="Describe what is happening" hint="Example: 'my father has chest pain and is sweating'"><textarea className="input" rows={3} maxLength={1500} value={text} onChange={(e) => setText(e.target.value)} required /></Field>
        <button className="btn mt-3" disabled={busy}>{busy ? <Spinner /> : <Search className="h-4 w-4" />} Check urgency</button>
        <div className="mt-3"><ErrorBox message={err} /></div>
      </form>
      {out && (
        <div className={`card mt-4 ${out.level === 'emergency' ? '!bg-red-50 ring-red-300' : ''}`}>
          <span className={`badge ${RISK_STYLE[out.level]}`}>{out.level.toUpperCase()}</span>
          <h3 className="mt-2 text-lg font-bold">{out.headline}</h3>
          {out.flags.length > 0 && <p className="text-sm text-red-700">Detected: {out.flags.join(', ')}</p>}
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{out.actions.map((a) => <li key={a}>{a}</li>)}</ul>
          {out.call && <a href={`tel:${out.call.number}`} className="btn-danger mt-4"><Phone className="h-4 w-4" /> {out.call.label}</a>}
          <p className="mt-3 text-xs text-slate-500">{out.note}</p>
        </div>
      )}
    </div>
  )
}

function Nearby() {
  const [pos, setPos] = useState(null)
  const [kind, setKind] = useState('hospital')
  const [places, setPlaces] = useState([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [ambs, setAmbs] = useState([])
  const [manualAddress, setManualAddress] = useState('')

  const search = async (p = pos, k = kind) => {
    if (!p) return
    setBusy(true); setErr('')
    try {
      setPlaces(await api.nearby(k, p.lat, p.lon))
      setAmbs(await api.ambulances(p.lat, p.lon))
    } catch (x) {
      setErr(x.message); setPlaces([])
    } finally {
      setBusy(false)
    }
  }

  const handleManualSearch = async (e) => {
    e.preventDefault()
    if (!manualAddress.trim()) return
    
    setBusy(true); setErr('')
    try {
      // 1. Get coordinates from the typed address
      const coords = await api.geocode(manualAddress)
      const newPos = { lat: coords.lat, lon: coords.lon }
      
      // 2. Update the map center and search
      setPos(newPos)
      await search(newPos, kind)
    } catch (x) {
      setErr(x.message)
      setPlaces([])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <LocateButton 
          onLocate={(p) => { setPos(p); search(p, kind) }} 
          label={pos ? 'Update my location' : 'Use my location'} 
        />
        
        {/* Manual Address Search */}
        <form onSubmit={handleManualSearch} className="flex flex-1 gap-2 min-w-[250px]">
          <input 
            className="input flex-1" 
            placeholder="Or type a city/area (e.g. Kolkata)..." 
            value={manualAddress}
            onChange={(e) => setManualAddress(e.target.value)}
          />
          <button type="submit" className="btn" disabled={busy || !manualAddress.trim()}>
            <Search className="h-4 w-4" /> Search
          </button>
        </form>

        <select 
          className="input max-w-[180px]" 
          value={kind} 
          onChange={(e) => { setKind(e.target.value); search(pos, e.target.value) }}
        >
          <option value="hospital">Hospitals</option>
          <option value="clinic">Clinics & doctors</option>
          <option value="pharmacy">Pharmacies</option>
          <option value="blood_bank">Blood banks</option>
        </select>
        {busy && <Spinner />}
      </div>

      <ErrorBox message={err} />
      
      {!pos && (
        <p className="text-sm text-slate-600">
          Share your location or type a city/area above to see the closest facilities on a map.
        </p>
      )}
      
      {pos && (
        <MapView 
          center={[pos.lat, pos.lon]} 
          places={[...places, ...ambs.map((a) => ({ ...a, name: `${a.operator} (${a.vehicle_type})`, kind: 'ambulance' }))]} 
        />
      )}
      
      {pos && !busy && places.length === 0 && !err && (
        <p className="mt-3 text-sm text-slate-600">
          Nothing found within 5 km in the map data. Try searching a nearby larger city or call the emergency number if urgent.
        </p>
      )}
      
      <ul className="mt-4 divide-y divide-slate-100">
        {places.slice(0, 10).map((p, i) => (
          <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
            <div>
              <b>{p.name}</b>
              {p.emergency === 'yes' && <span className="badge ml-2 bg-red-100 text-red-700">Emergency</span>}
              <div className="text-xs text-slate-500">{p.distance_km} km{p.address ? ` · ${p.address}` : ''}</div>
            </div>
            <div className="flex gap-2">
              {p.phone && (
                <a className="btn-ghost !py-1.5" href={`tel:${String(p.phone).split(/[;,]/)[0]}`}>
                  <Phone className="h-4 w-4" />
                </a>
              )}
              <a className="btn-ghost !py-1.5" target="_blank" rel="noreferrer" href={googleDirections(p.lat, p.lon)}>
                Directions
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

const FLOW = ['requested', 'dispatched', 'on_the_way', 'arrived', 'completed']

function Ambulance({ numbers }) {
  const [f, setF] = useState({ patient_name: '', phone: '', emergency_type: '', severity: 'urgent', address: '' })
  const [pos, setPos] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [out, setOut] = useState(null), [track, setTrack] = useState(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    if (!pos) return setErr('Please share your location so responders can find you.')
    setBusy(true); setErr('')
    try { const r = await api.requestAmbulance({ ...f, ...pos }); setOut(r); setTrack({ status: 'requested' }) } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  useEffect(() => { // poll status every 10 s while a request is active
    if (!out) return
    const id = setInterval(() => api.ambulanceStatus(out.id, f.phone).then(setTrack).catch(() => { }), 10000)
    return () => clearInterval(id)
  }, [out]) // eslint-disable-line
  return (
    <div>
      <div className="mb-4 flex items-start gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 ring-1 ring-amber-200"><AlertOctagon className="mt-0.5 h-4 w-4 shrink-0" /> If this is life-threatening, call <b className="mx-1">{numbers?.ambulance || '108'}</b> first. This form coordinates community and registered ambulance operators and cannot guarantee a response.</div>
      <form className="card" onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Patient name"><input className="input" value={f.patient_name} onChange={set('patient_name')} required /></Field>
          <Field label="Contact phone"><input className="input" type="tel" value={f.phone} onChange={set('phone')} required /></Field>
          <Field label="Emergency type"><input className="input" placeholder="Accident, chest pain, pregnancy…" value={f.emergency_type} onChange={set('emergency_type')} required /></Field>
          <Field label="Severity"><select className="input" value={f.severity} onChange={set('severity')}><option value="urgent">Urgent</option><option value="critical">Critical</option></select></Field>
          <Field label="Landmark / address (optional)"><input className="input" value={f.address} onChange={set('address')} /></Field>
          <div className="flex items-end"><LocateButton onLocate={setPos} label={pos ? 'Location captured ✓' : 'Share pickup location'} /></div>
        </div>
        <div className="mt-3"><ErrorBox message={err} /></div>
        <button className="btn-danger mt-4" disabled={busy}>{busy ? <Spinner /> : <AmbIcon className="h-4 w-4" />} Request ambulance</button>
      </form>
      {out && (
        <div className="card mt-4">
          <h3 className="font-bold">Request #{out.id} · save this number</h3>
          <p className="mt-1 rounded-lg bg-red-50 p-2 text-sm text-red-700">{out.warning}</p>
          <ol className="mt-4 flex flex-wrap gap-2 text-xs">{FLOW.map((s) => <li key={s} className={`badge ${FLOW.indexOf(s) <= FLOW.indexOf(track?.status) ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{s.replace('_', ' ')}</li>)}</ol>
          {track?.ambulance && <p className="mt-3 text-sm">Assigned: <b>{track.ambulance.operator}</b> ({track.ambulance.vehicle_type}) · <a className="font-semibold text-brand-700 underline" href={`tel:${track.ambulance.phone}`}>{track.ambulance.phone}</a></p>}
          <h4 className="mt-4 text-sm font-bold">Nearest registered ambulances - call directly</h4>
          {out.suggested_ambulances.length === 0 ? <p className="text-sm text-slate-600">No verified ambulances registered nearby yet. Call {numbers?.ambulance || '108'}.</p> :
            <ul className="mt-1 divide-y divide-slate-100">{out.suggested_ambulances.map((a) => <li key={a.id} className="flex items-center justify-between py-2 text-sm"><span><b>{a.operator}</b> · {a.vehicle_type} · {a.distance_km} km</span><a className="btn !py-1.5" href={`tel:${a.phone}`}><Phone className="h-4 w-4" /> Call</a></li>)}</ul>}
        </div>
      )}
    </div>
  )
}

function Provider() {
  const [f, setF] = useState({ operator: '', phone: '', vehicle_type: 'BLS', city: '' })
  const [pos, setPos] = useState(null), [busy, setBusy] = useState(false), [err, setErr] = useState(''), [ok, setOk] = useState('')
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    if (!pos) return setErr('Share the ambulance base location first.')
    setBusy(true); setErr('')
    try { setOk((await api.registerAmbulance({ ...f, ...pos })).message) } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }
  return (
    <form className="card" onSubmit={submit}>
      <p className="mb-4 text-sm text-slate-600">Own or operate an ambulance? Register it. Listings appear publicly only after verification by an administrator.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Operator / organisation"><input className="input" value={f.operator} onChange={set('operator')} required /></Field>
        <Field label="Dispatch phone"><input className="input" type="tel" value={f.phone} onChange={set('phone')} required /></Field>
        <Field label="Vehicle type"><select className="input" value={f.vehicle_type} onChange={set('vehicle_type')}><option value="BLS">Basic life support</option><option value="ALS">Advanced life support</option><option value="NEONATAL">Neonatal</option><option value="MORTUARY">Mortuary van</option></select></Field>
        <Field label="City"><input className="input" value={f.city} onChange={set('city')} required /></Field>
        <div className="flex items-end"><LocateButton onLocate={setPos} label={pos ? 'Base location saved ✓' : 'Use current location as base'} /></div>
      </div>
      <div className="mt-3"><ErrorBox message={err} /></div>{ok && <p className="mt-3 text-sm font-semibold text-emerald-700">{ok}</p>}
      <button className="btn mt-4" disabled={busy}>{busy && <Spinner />} Submit for verification</button>
    </form>
  )
}

export default function Emergency() {
  const [tab, setTab] = useState('triage')
  const [numbers, setNumbers] = useState(null)
  useEffect(() => { api.numbers().then(setNumbers).catch(() => setNumbers({ ambulance: '108', national_emergency: '112', ambulance_alt: '102', women_helpline: '1091' })) }, [])
  return (
    <div>
      <PageTitle icon={Siren} title="Emergency" subtitle={`Quick help. Numbers shown for ${numbers?.country || 'India'}.`} />
      <Numbers n={numbers} />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: 'triage', label: 'Symptom triage' }, { value: 'nearby', label: 'Nearby hospitals' }, { value: 'ambulance', label: 'Request ambulance' }, { value: 'provider', label: 'Register ambulance' }]} />
      {tab === 'triage' && <Triage />}
      {tab === 'nearby' && <Nearby />}
      {tab === 'ambulance' && <Ambulance numbers={numbers} />}
      {tab === 'provider' && <Provider />}
    </div>
  )
}