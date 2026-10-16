import { useEffect, useState } from 'react'
import { History as HistoryIcon, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import ActivityList from '../components/ActivityList'
import { ErrorBox, PageTitle, RISK_STYLE, Spinner, Tabs } from '../components/ui'

const FILTERS = {
  all: null,
  screenings: ['diagnosis'],
  blood: ['blood_request', 'blood_request_closed', 'donor_registered', 'donor_removed'],
  emergency: ['ambulance_request', 'ambulance_registered'],
  tools: ['report_analyzed'],
  account: ['account'],
}

function Screenings({ rows, reload }) {
  const clear = async () => { if (confirm('Delete all your saved screenings?')) { await api.clearHistory(); reload() } }
  if (!rows.length) return <div className="card text-sm text-slate-600">No screenings yet. Run one on the Diagnosis page.</div>
  return (
    <div className="card">
      <div className="mb-3 flex justify-end"><button className="btn-ghost" onClick={clear}><Trash2 className="h-4 w-4" /> Delete all</button></div>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm">
        <thead className="text-xs text-slate-500"><tr><th className="py-1">Date</th><th>Screening</th><th>Probability</th><th>Risk</th><th>Model</th></tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.id} className="border-t border-slate-100">
            <td className="py-2">{new Date(r.created_at).toLocaleString()}</td>
            <td className="capitalize">{r.disease}</td><td>{Math.round(r.probability * 100)}%</td>
            <td><span className={`badge ${RISK_STYLE[r.risk_level]}`}>{r.risk_level}</span></td><td className="text-slate-500">{r.model}</td>
          </tr>))}</tbody>
      </table></div>
    </div>
  )
}

export default function History() {
  const [tab, setTab] = useState('activity')
  const [filter, setFilter] = useState('all')
  const [screenings, setScreenings] = useState(null), [activity, setActivity] = useState(null), [error, setError] = useState('')
  const loadScreenings = () => api.history().then(setScreenings).catch((e) => setError(e.message))
  useEffect(() => { loadScreenings(); api.activity(200).then(setActivity).catch((e) => setError(e.message)) }, [])

  const shown = activity && (FILTERS[filter] ? activity.filter((a) => FILTERS[filter].includes(a.type)) : activity)
  return (
    <div>
      <PageTitle icon={HistoryIcon} title="My History" subtitle="Everything you've done on VitalAI, tied to your account." />
      <ErrorBox message={error} />
      <Tabs value={tab} onChange={setTab} tabs={[{ value: 'activity', label: 'All activity' }, { value: 'screenings', label: 'Screenings' }]} />
      {tab === 'activity' && (
        <div className="card">
          <div className="mb-2 flex flex-wrap gap-2">
            {Object.keys(FILTERS).map((k) => (
              <button key={k} onClick={() => setFilter(k)} className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${filter === k ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>{k}</button>
            ))}
          </div>
          {!shown ? <p className="py-4 text-sm text-slate-500"><Spinner className="inline" /> Loading…</p> : <ActivityList items={shown} empty="No activity in this category yet." />}
        </div>
      )}
      {tab === 'screenings' && (!screenings ? <p className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> Loading…</p> : <Screenings rows={screenings} reload={loadScreenings} />)}
    </div>
  )
}
