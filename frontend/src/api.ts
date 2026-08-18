import type { Finding, HistoricalScan, ScanDetail, ScanResponse } from './types'

export type { ScanResponse }
export type { Severity, Finding, HistoricalScan, ScanDetail } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

export interface ScanPayload {
  code: string
  filename: string
  enrich?: boolean
  llm_missed_issues?: boolean
}

export interface ScanJob {
  scan_id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  total_files: number
  scanned_files: number
  total_issues: number
  risk_score: number
  findings: Finding[]
  per_file: { file: string; total_issues: number }[]
  error: string | null
  user_id?: string | null
  label?: string
  source_type?: string
}

export interface ScanStreamEvent {
  type: 'status' | 'progress' | 'file' | 'snapshot' | 'done' | 'failed'
  status?: string
  scanned?: number
  total?: number
  file?: string
  findings?: Finding[]
  scan_id?: string
  filename?: string
  total_files?: number
  total_issues?: number
  risk_score?: number
  error?: string
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => null)
    throw new Error(
      typeof err?.detail === 'string' ? err.detail : `Request failed (HTTP ${res.status})`,
    )
  }
  return res.json()
}

function authHeader(token?: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function createScanJob(
  payload: ScanPayload,
  token?: string | null,
): Promise<ScanJob> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify(payload),
  })
  return handle<ScanJob>(res)
}

export async function startRepoScan(
  github_url: string,
  branch?: string,
  token?: string | null,
): Promise<ScanJob> {
  const res = await fetch(`${API_BASE}/scan/repo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify({ github_url, branch: branch || null }),
  })
  return handle<ScanJob>(res)
}

export async function startZipScan(
  file: File,
  token?: string | null,
): Promise<ScanJob> {
  const form = new FormData()
  form.append('file', file)
  form.append('enrich', 'true')
  form.append('llm_missed_issues', 'true')
  const res = await fetch(`${API_BASE}/scan/repo/zip`, {
    method: 'POST',
    headers: authHeader(token),
    body: form,
  })
  return handle<ScanJob>(res)
}

export function scanEventsUrl(scanId: string): string {
  return `${API_BASE}/scan/${scanId}/events`
}

export function subscribeScan(
  scanId: string,
  handlers: {
    onEvent: (e: ScanStreamEvent) => void
    onEnd: () => void
    onError?: (message: string) => void
  },
): () => void {
  const source = new EventSource(scanEventsUrl(scanId))
  let closed = false
  source.onmessage = (msg) => {
    let evt: ScanStreamEvent
    try {
      evt = JSON.parse(msg.data)
    } catch {
      return
    }
    handlers.onEvent(evt)
    if (evt.type === 'done' || evt.type === 'failed') {
      closed = true
      source.close()
      handlers.onEnd()
    }
  }
  source.onerror = () => {
    if (!closed) {
      closed = true
      source.close()
      handlers.onError?.('Connection to scan stream lost')
    }
  }
  return () => {
    closed = true
    source.close()
  }
}

export async function listScans(
  token: string,
): Promise<{ scans: HistoricalScan[]; storage: string }> {
  const res = await fetch(`${API_BASE}/scans`, { headers: authHeader(token) })
  return handle(res)
}

export async function getHistoricalScan(
  token: string,
  scanId: string,
): Promise<ScanDetail> {
  const res = await fetch(`${API_BASE}/scans/${scanId}`, {
    headers: authHeader(token),
  })
  return handle<ScanDetail>(res)
}

export async function deleteHistoricalScan(
  token: string,
  scanId: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/scans/${scanId}`, {
    method: 'DELETE',
    headers: authHeader(token),
  })
  if (!res.ok) await handle(res)
}

export async function fetchMe(
  token: string,
): Promise<{ user_id: string; storage: string }> {
  const res = await fetch(`${API_BASE}/me`, { headers: authHeader(token) })
  return handle(res)
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) })
    return res.ok
  } catch {
    return false
  }
}