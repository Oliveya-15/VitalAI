import { useEffect, useState } from 'react'
import { Stethoscope, Brain, TrendingUp, TrendingDown } from 'lucide-react'
import { api } from '../services/api'
import { Disclaimer, ErrorBox, Field, PageTitle, RISK_STYLE, Spinner, Tabs } from '../components/ui'

const TABS = [
  { value: 'diabetes', label: 'Diabetes' },
  { value: 'heart', label: 'Heart disease' },
  { value: 'parkinsons', label: "Parkinson's" },
]

function Result({ r }) {
  const pct = Math.round(r.probability * 100)
  const bar = r.risk_level === 'high' ? 'bg-red-500' : r.risk_level === 'moderate' ? 'bg-amber-500' : 'bg-emerald-500'
  const maxImpact = Math.max(...r.top_factors.map((f) => Math.abs(f.impact)), 0.01)
  return (
    <div className="card mt-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-lg font-bold">Screening result</h3>
        <span className={`badge ${RISK_STYLE[r.risk_level]}`}>{r.risk_level.toUpperCase()} RISK</span>
      </div>
      <p className="mt-2 text-sm text-slate-600">Estimated probability of {r.title.toLowerCase()} pattern: <b>{pct}%</b></p>
      <div className="mt-2 h-3 w-full rounded-full bg-slate-100"><div className={`h-3 rounded-full ${bar}`} style={{ width: `${pct}%` }} /></div>

      <h4 className="mt-5 flex items-center gap-1 text-sm font-bold"><Brain className="h-4 w-4" /> What influenced this result</h4>
      <p className="text-xs text-slate-500">Estimated by replacing each value with a typical one and measuring the change.</p>
      <ul className="mt-2 space-y-2">
        {r.top_factors.map((f) => (
          <li key={f.feature} className="text-sm">
            <div className="flex items-center justify-between">
              <span>{f.label} <span className="text-slate-400">({f.value})</span></span>
              <span className={`flex items-center gap-1 text-xs font-semibold ${f.impact > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {f.impact > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {f.impact > 0 ? 'raises' : 'lowers'} risk
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-slate-100"><div className={`h-1.5 rounded-full ${f.impact > 0 ? 'bg-red-400' : 'bg-emerald-400'}`} style={{ width: `${(Math.abs(f.impact) / maxImpact) * 100}%` }} /></div>
          </li>
        ))}
      </ul>
      <p className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">Model: <b>{r.model}</b> · held-out accuracy {Math.round(r.model_metrics.accuracy * 100)}% · ROC-AUC {r.model_metrics.roc_auc}. {r.disclaimer}</p>
    </div>
  )
}

export default function Diagnosis() {
  const [disease, setDisease] = useState('diabetes')
  const [schema, setSchema] = useState(null)
  const [vals, setVals] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setSchema(null); setResult(null); setError(''); setVals({})
    api.schema(disease).then(setSchema).catch((e) => setError(e.message))
  }, [disease])

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      const numeric = {}
      for (const f of schema.features) {
        const raw = vals[f.name]
        if (raw === undefined || raw === '' || Number.isNaN(Number(raw))) throw new Error(`Please enter a valid number for "${f.label}".`)
        numeric[f.name] = Number(raw)
      }
      setResult(await api.predict(disease, numeric))
    } catch (err) { setError(err.message); setResult(null) } finally { setBusy(false) }
  }

  const fillExample = () => {
    if (!schema) return
    setVals(Object.fromEntries(schema.features.map((f) => [f.name, String(Math.round(f.median * 1000) / 1000)])))
  }

  return (
    <div>
      <PageTitle icon={Stethoscope} title="AI Diagnosis" subtitle="Machine-learning screening models. Enter clinical values from a recent test." />
      <Tabs tabs={TABS} value={disease} onChange={setDisease} />
      {!schema && !error && <p className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> Loading form… (the server may be waking up)</p>}
      <ErrorBox message={error} />
      {schema && (
        <form onSubmit={submit} className="card mt-3">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <span>Model: <b>{schema.best_model}</b> (best of {schema.leaderboard.length} compared) · trained on {schema.n_samples} records</span>
            <button type="button" className="font-semibold text-brand-700 underline" onClick={fillExample}>Fill with typical values</button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {schema.features.map((f) => {
              const isSelect = f.kind.startsWith('select:')
              return (
                <Field key={f.name} label={f.label} hint={f.hint}>
                  {isSelect ? (
                    <select className="input" value={vals[f.name] ?? ''} onChange={(e) => setVals({ ...vals, [f.name]: e.target.value })}>
                      <option value="">Select…</option>
                      {f.kind.slice(7).split(',').map((o) => { const [v, l] = o.split('='); return <option key={v} value={v}>{l}</option> })}
                    </select>
                  ) : (
                    <input className="input" type="number" step="any" inputMode="decimal" value={vals[f.name] ?? ''} onChange={(e) => setVals({ ...vals, [f.name]: e.target.value })} />
                  )}
                </Field>
              )
            })}
          </div>
          <button className="btn mt-5" disabled={busy}>{busy && <Spinner />} Analyse</button>
          <Disclaimer>Screening estimate only - not a diagnosis.</Disclaimer>
        </form>
      )}
      {result && <Result r={result} />}
    </div>
  )
}
