import { useEffect, useState } from 'react'
import { History as HistoryIcon, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, PageTitle, RISK_STYLE, Spinner } from '../components/ui'

export default function History() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const load = () => api.history().then(setRows).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])
  const clear = async () => { if (confirm('Delete all your saved assessments?')) { await api.clearHistory(); load() } }

  return (
    <div>
      <PageTitle icon={HistoryIcon} title="My History" subtitle="Your previous screenings, stored anonymously against a random ID in this browser." />
      <ErrorBox message={error} />
      {!rows && !error && <p className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> Loading…</p>}
      {rows && rows.length === 0 && <div className="card text-sm text-slate-600">No assessments yet. Run one on the Diagnosis page.</div>}
      {rows && rows.length > 0 && (
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
      )}
    </div>
  )
}
