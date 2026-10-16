import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'

function Centered({ children }) {
  return <div className="flex min-h-screen items-center justify-center bg-mint p-6"><div className="card max-w-sm text-center">{children}</div></div>
}

/** Only signed-in users get through; everyone else is sent to /login (and returned afterwards). */
export default function ProtectedRoute({ children }) {
  const { status, retry } = useAuth()
  const loc = useLocation()
  if (status === 'loading') {
    return <Centered><Spinner className="mx-auto h-6 w-6 text-brand-600" /><p className="mt-3 text-sm text-slate-600">Checking your session…<br /><span className="text-xs text-slate-400">The server may take up to a minute to wake up.</span></p></Centered>
  }
  if (status === 'error') {
    return <Centered><p className="font-semibold">Can't reach the server</p><p className="mt-1 text-sm text-slate-600">Your session is safe - please check your connection and try again.</p><button className="btn mt-4" onClick={retry}>Try again</button></Centered>
  }
  if (status === 'anon') return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  return children
}

/** Login/Register pages: signed-in users are bounced to the dashboard. */
export function PublicOnly({ children }) {
  const { status } = useAuth()
  if (status === 'authed') return <Navigate to="/" replace />
  return children
}
