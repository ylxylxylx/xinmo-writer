const BASE = '/api'

export async function apiGet(path) {
  const res = await fetch(BASE + path)
  if (!res.ok) { const e = await res.json().catch(() => {}); throw new Error(e?.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function apiPost(path, data) {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(data),
  })
  const json = await res.json()
  if (json.error) throw new Error(json.error)
  return json
}

export async function apiPut(path, data) {
  const res = await fetch(BASE + path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams(data),
  })
  const json = await res.json()
  if (json.error) throw new Error(json.error)
  return json
}

export async function apiDelete(path) {
  const res = await fetch(BASE + path, { method: 'DELETE' })
  if (!res.ok) { const e = await res.json().catch(() => {}); throw new Error(e?.detail || `HTTP ${res.status}`) }
  return res.json()
}
