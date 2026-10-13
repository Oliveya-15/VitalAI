import { useEffect, useRef, useState } from 'react'
import { Bot, Send, User, Phone, MapPin, Sparkles } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, PageTitle, Spinner } from '../components/ui'

const SUGGESTIONS = [
  'What are the early signs of diabetes?',
  'Who can donate blood?',
  'How do I do CPR on an adult?',
  'My blood sugar was 160 fasting, what does that mean?',
]

/** Minimal safe renderer: **bold**, "- " bullets, paragraphs. No HTML injection. */
function Rich({ text }) {
  const inline = (s) => s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') ? <b key={i}>{p.slice(2, -2)}</b> : <span key={i}>{p}</span>))
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {text.split('\n').map((ln, i) => {
        if (!ln.trim()) return <div key={i} className="h-1" />
        if (/^\s*[-*] /.test(ln)) return <div key={i} className="flex gap-2 pl-1"><span>•</span><span>{inline(ln.replace(/^\s*[-*] /, ''))}</span></div>
        return <p key={i}>{inline(ln)}</p>
      })}
    </div>
  )
}

export default function Assistant() {
  const [msgs, setMsgs] = useState([{ role: 'assistant', content: "Hi, I'm VitalAI. Ask me about symptoms, first aid, blood donation or health conditions. I can also run our screening models if you share clinical values." }])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [loc, setLoc] = useState(null)
  const [status, setStatus] = useState(null)
  const end = useRef(null)

  useEffect(() => { api.assistantStatus().then(setStatus).catch(() => {}) }, [])
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const shareLocation = () => navigator.geolocation?.getCurrentPosition((p) => setLoc({ lat: p.coords.latitude, lon: p.coords.longitude }), () => setError('Location permission denied.'))

  const send = async (text) => {
    const message = (text ?? input).trim()
    if (!message || busy) return
    setInput(''); setError('')
    const history = msgs.filter((m, i) => i > 0).map(({ role, content }) => ({ role, content }))
    setMsgs((m) => [...m, { role: 'user', content: message }])
    setBusy(true)
    try {
      const r = await api.chat(message, history, loc)
      setMsgs((m) => [...m, { role: 'assistant', content: r.reply, meta: r }])
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <PageTitle icon={Bot} title="AI Health Assistant" subtitle="An AI agent with a medical knowledge base, emergency detection and access to the platform's tools." />
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`badge ${status?.llm_enabled ? 'bg-sky-100 text-sky-700' : 'bg-slate-200 text-slate-600'}`}><Sparkles className="mr-1 h-3 w-3" />{status?.llm_enabled ? `LLM agent · ${status.model}` : 'Knowledge-base mode (no LLM key configured)'}</span>
        <button className={`badge ${loc ? 'bg-emerald-100 text-emerald-700' : 'bg-white ring-1 ring-slate-300 text-slate-600'}`} onClick={shareLocation}><MapPin className="mr-1 h-3 w-3" />{loc ? 'Location shared' : 'Share location for nearby-hospital questions'}</button>
      </div>
      <div className="card flex h-[60vh] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto pr-1">
          {msgs.map((m, i) => (
            <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
              {m.role === 'assistant' && <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700"><Bot className="h-4 w-4" /></div>}
              <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${m.role === 'user' ? 'bg-brand-600 text-white' : m.meta?.mode === 'safety_triage' ? 'bg-red-50 ring-1 ring-red-200' : 'bg-slate-100'}`}>
                <Rich text={m.content} />
                {m.meta?.triage?.call && (
                  <a href={`tel:${m.meta.triage.call.number}`} className="btn-danger mt-3 !py-2"><Phone className="h-4 w-4" /> {m.meta.triage.call.label}</a>
                )}
                {m.meta?.sources?.length > 0 && <p className="mt-2 text-[11px] text-slate-500">Sources: {[...new Set(m.meta.sources.map((s) => s.title))].join(' · ')}</p>}
                {m.meta?.tools_used?.length > 0 && m.meta.mode === 'llm_agent' && <p className="mt-1 text-[11px] text-slate-400">Tools used: {[...new Set(m.meta.tools_used)].join(', ')}</p>}
              </div>
              {m.role === 'user' && <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-200"><User className="h-4 w-4" /></div>}
            </div>
          ))}
          {busy && <p className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> Thinking…</p>}
          <div ref={end} />
        </div>
        {msgs.length === 1 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => <button key={s} className="rounded-full bg-white px-3 py-1.5 text-xs text-slate-600 ring-1 ring-slate-300 hover:bg-slate-50" onClick={() => send(s)}>{s}</button>)}
          </div>
        )}
        <ErrorBox message={error} />
        <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send() }}>
          <input className="input" placeholder="Ask a health question…" value={input} maxLength={1500} onChange={(e) => setInput(e.target.value)} />
          <button className="btn" disabled={busy || !input.trim()} aria-label="Send"><Send className="h-4 w-4" /></button>
        </form>
      </div>
      <p className="mt-2 text-xs text-slate-500">General information only - not medical advice. For emergencies call your ambulance number.</p>
    </div>
  )
}
