// Same-origin in production (the built UI is served by the same FastAPI
// app it calls, see app/api/main.py's static-file mount) -- localhost:8010
// only in local dev, where Vite's dev server (:5180) and the API
// (uvicorn, :8010) run as separate processes. FIXED 2026-07-28: this was
// hardcoded to localhost:8010 unconditionally, baked into the production
// build -- every deployed browser tried to reach the VIEWER's own
// laptop, not the real server, silently failing every API call.
export const BASE_URL = import.meta.env.DEV ? 'http://localhost:8010' : ''


export async function apiFetch(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function authedFetch(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  }
  return fetch(`${BASE_URL}${path}`, { ...options, headers })
}

export async function apiPost(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `API error: ${res.status}`)
  return data
}
