import { useState } from 'react'
import { Wrench, Scale, HeartPulse, FileText } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, Field, PageTitle, RISK_STYLE, Spinner } from '../components/ui'

function useCall(fn) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const run = async (...a) => { setBusy(true); setError(''); try { setData(await fn(...a)) } catch (e) { setError(e.message); setData(null) } finally { setBusy(false) } }
  return { data, error, busy, run }
}

function BMI() {
  const [w, setW] = useState(''), [h, setH] = useState('')
  const c = useCall(api.bmi)
  return (
    <form className="card" onSubmit={(e) => { e.preventDefault(); c.run({ weight_kg: +w, height_cm: +h }) }}>
      <h2 className="flex items-center gap-2 font-bold"><Scale className="h-5 w-5 text-brand-600" /> BMI calculator</h2>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Field label="Weight (kg)"><input className="input" type="number" step="any" value={w} onChange={(e) => setW(e.target.value)} required /></Field>
        <Field label="Height (cm)"><input className="input" type="number" step="any" value={h} onChange={(e) => setH(e.target.value)} required /></Field>
      </div>
      <button className="btn mt-3" disabled={c.busy}>{c.busy && <Spinner />} Calculate</button>
      <div className="mt-3"><ErrorBox message={c.error} /></div>
      {c.data && <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm"><b className="text-xl">{c.data.bmi}</b> · {c.data.category}<br />Healthy weight for your height: {c.data.healthy_weight_range_kg[0]}–{c.data.healthy_weight_range_kg[1]} kg<p className="mt-1 text-xs text-slate-500">{c.data.note}</p></div>}
    </form>
  )
}

function BP() {
  const [s, setS] = useState(''), [d, setD] = useState('')
  const c = useCall(api.bp)
  return (
    <form className="card" onSubmit={(e) => { e.preventDefault(); c.run({ systolic: +s, diastolic: +d }) }}>
      <h2 className="flex items-center gap-2 font-bold"><HeartPulse className="h-5 w-5 text-red-500" /> Blood-pressure check</h2>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Field label="Systolic (top)"><input className="input" type="number" value={s} onChange={(e) => setS(e.target.value)} required /></Field>
        <Field label="Diastolic (bottom)"><input className="input" type="number" value={d} onChange={(e) => setD(e.target.value)} required /></Field>
      </div>
      <button className="btn mt-3" disabled={c.busy}>{c.busy && <Spinner />} Check</button>
      <div className="mt-3"><ErrorBox message={c.error} /></div>
      {c.data && <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm"><span className={`badge ${RISK_STYLE[c.data.level === 'high' ? 'high' : c.data.level]}`}>{c.data.category}</span><p className="mt-2">{c.data.advice}</p></div>}
    </form>
  )
}

const SAMPLE = 'Fasting Glucose: 118 mg/dL\nHbA1c: 6.1 %\nTotal Cholesterol: 214 mg/dL\nLDL: 138 mg/dL\nHDL: 38 mg/dL\nTriglycerides: 190 mg/dL\nHaemoglobin: 13.1 g/dL'
const STATUS = { normal: 'bg-emerald-100 text-emerald-700', borderline: 'bg-amber-100 text-amber-700', high: 'bg-red-100 text-red-700', low: 'bg-sky-100 text-sky-700' }

function Report() {
  const [text, setText] = useState(''), [sex, setSex] = useState('')
  const c = useCall(api.report)
  return (
    <form className="card lg:col-span-2" onSubmit={(e) => { e.preventDefault(); c.run({ text, sex: sex || null }) }}>
      <h2 className="flex items-center gap-2 font-bold"><FileText className="h-5 w-5 text-violet-600" /> Lab report reader</h2>
      <p className="text-xs text-slate-500">Paste lines from your report (one test per line). Supported: fasting glucose, HbA1c, cholesterol, LDL, HDL, triglycerides, TSH, haemoglobin.</p>
      <textarea className="input mt-3 h-36 font-mono" placeholder={SAMPLE} value={text} onChange={(e) => setText(e.target.value)} required />
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <Field label="Sex (for haemoglobin range)"><select className="input" value={sex} onChange={(e) => setSex(e.target.value)}><option value="">Not specified</option><option value="female">Female</option><option value="male">Male</option></select></Field>
        <button className="btn" disabled={c.busy}>{c.busy && <Spinner />} Analyse</button>
        <button type="button" className="btn-ghost" onClick={() => setText(SAMPLE)}>Use sample</button>
      </div>
      <div className="mt-3"><ErrorBox message={c.error} /></div>
      {c.data && (c.data.results.length === 0
        ? <p className="mt-3 text-sm text-slate-600">No supported tests were recognised. Try the format “Test name: value”.</p>
        : <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs text-slate-500"><tr><th className="py-1">Test</th><th>Value</th><th>Status</th><th>Note</th></tr></thead><tbody>
          {c.data.results.map((r) => <tr key={r.test} className="border-t border-slate-100"><td className="py-2 font-semibold">{r.test}</td><td>{r.value} {r.unit}</td><td><span className={`badge ${STATUS[r.status]}`}>{r.status}</span></td><td className="text-slate-600">{r.note}</td></tr>)}
        </tbody></table><p className="mt-2 text-xs text-slate-500">{c.data.note}</p></div>)}
    </form>
  )
}

export default function Tools() {
  return (
    <div>
      <PageTitle icon={Wrench} title="Health Tools" subtitle="Quick calculators and a lab report reader. Results use standard published reference ranges." />
      <div className="grid gap-4 lg:grid-cols-2"><BMI /><BP /><Report /></div>
    </div>
  )
}
