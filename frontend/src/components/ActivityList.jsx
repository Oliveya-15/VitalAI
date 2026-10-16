import { Link } from 'react-router-dom'
import { Ambulance, Droplets, FileText, Stethoscope, UserCircle, HeartHandshake } from 'lucide-react'

// type -> [icon, tile colour, page it belongs to]
export const ACTIVITY_META = {
  diagnosis: [Stethoscope, 'bg-brand-50 text-brand-600', '/diagnosis'],
  blood_request: [Droplets, 'bg-red-50 text-red-500', '/blood'],
  blood_request_closed: [Droplets, 'bg-red-50 text-red-500', '/blood'],
  donor_registered: [HeartHandshake, 'bg-red-50 text-red-500', '/blood'],
  donor_removed: [HeartHandshake, 'bg-slate-100 text-slate-500', '/blood'],
  ambulance_request: [Ambulance, 'bg-red-50 text-red-500', '/emergency'],
  ambulance_registered: [Ambulance, 'bg-red-50 text-red-500', '/emergency'],
  report_analyzed: [FileText, 'bg-violet-50 text-violet-500', '/tools'],
  account: [UserCircle, 'bg-sky-50 text-sky-500', '/profile'],
}

export function timeAgo(iso) {
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000))
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60); if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60); if (h < 24) return `${h} hr ago`
  const d = Math.floor(h / 24); if (d < 7) return `${d} day${d > 1 ? 's' : ''} ago`
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function ActivityList({ items, empty = 'No activity yet.' }) {
  if (!items.length) return <p className="py-4 text-sm text-slate-500">{empty}</p>
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((a) => {
        const [Icon, tone, to] = ACTIVITY_META[a.type] || ACTIVITY_META.account
        return (
          <li key={a.id}>
            <Link to={to} className="flex items-center gap-3 py-3 transition hover:bg-slate-50 sm:px-2">
              <span className={`rounded-xl p-2 ${tone}`}><Icon className="h-4 w-4" /></span>
              <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{a.title}</span>
                <span className="text-xs text-slate-500" title={new Date(a.created_at).toLocaleString()}>{timeAgo(a.created_at)}</span></span>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
