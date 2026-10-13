/** Single place for all backend calls. Base URL comes from VITE_API_BASE_URL at build time. */
const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/$/, '')

export function clientId() {
  let id = null
  try { id = localStorage.getItem('vitalai_client_id') } catch { /* storage blocked */ }
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()) + Math.random().toString(16).slice(2)
    try { localStorage.setItem('vitalai_client_id', id) } catch { /* ignore */ }
  }
  return id
}

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

async function req(path, { method = 'GET', body, headers = {}, timeoutMs = 70000 } = {}) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), timeoutMs) // free Render may need ~60s to wake up
  try {
    const res = await fetch(BASE + path, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-Client-Id': clientId(), ...headers },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    if (!res.ok) {
      let detail = `Request failed (${res.status})`
      try {
        const j = await res.json()
        if (typeof j.detail === 'string') detail = j.detail
        else if (Array.isArray(j.detail)) detail = j.detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join('; ')
      } catch { /* not json */ }
      throw new ApiError(detail, res.status)
    }
    return res.json()
  } catch (e) {
    if (e.name === 'AbortError') throw new ApiError('The server took too long to respond. It may be waking up - please try again.', 0)
    if (e instanceof ApiError) throw e
    throw new ApiError('Cannot reach the server. Check your connection or try again shortly.', 0)
  } finally {
    clearTimeout(t)
  }
}

export const api = {
  ping: () => req('/ping', { timeoutMs: 90000 }),
  models: () => req('/diagnosis/models'),
  schema: (d) => req(`/diagnosis/${d}/schema`),
  predict: (d, values) => req(`/diagnosis/${d}/predict`, { method: 'POST', body: { values } }),
  history: () => req('/diagnosis/history'),
  clearHistory: () => req('/diagnosis/history', { method: 'DELETE' }),
  chat: (message, history, loc) => req('/assistant/chat', { method: 'POST', body: { message, history, ...(loc || {}) } }),
  assistantStatus: () => req('/assistant/status'),
  bmi: (b) => req('/tools/bmi', { method: 'POST', body: b }),
  bp: (b) => req('/tools/blood-pressure', { method: 'POST', body: b }),
  report: (b) => req('/tools/report', { method: 'POST', body: b }),
  bloodStats: () => req('/blood/stats'),
  bloodCompat: () => req('/blood/compatibility'),
  registerDonor: (b) => req('/blood/donors', { method: 'POST', body: b }),
  optOut: (phone) => req('/blood/donors/opt-out', { method: 'POST', body: { phone } }),
  createBloodRequest: (b) => req('/blood/requests', { method: 'POST', body: b }),
  bloodRequests: (q = '') => req('/blood/requests' + q),
  closeBloodRequest: (id, phone, status) => req(`/blood/requests/${id}/status?contact_phone=${encodeURIComponent(phone)}`, { method: 'PATCH', body: { status } }),
  numbers: () => req('/emergency/numbers'),
  triage: (text) => req('/emergency/triage', { method: 'POST', body: { text } }),
  nearby: (kind, lat, lon) => req(`/emergency/nearby?kind=${kind}&lat=${lat}&lon=${lon}`, { timeoutMs: 40000 }),
  ambulances: (lat, lon) => req(`/emergency/ambulances${lat != null ? `?lat=${lat}&lon=${lon}` : ''}`),
  registerAmbulance: (b) => req('/emergency/ambulances', { method: 'POST', body: b }),
  requestAmbulance: (b) => req('/emergency/ambulance-requests', { method: 'POST', body: b }),
  ambulanceStatus: (id, phone) => req(`/emergency/ambulance-requests/${id}?phone=${encodeURIComponent(phone)}`),
}
