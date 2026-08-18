import { create } from 'zustand'
import {
  createScanJob,
  deleteHistoricalScan,
  getHistoricalScan,
  listScans,
  startRepoScan,
  startZipScan,
  subscribeScan,
  type HistoricalScan,
  type ScanJob,
  type ScanResponse,
  type ScanStreamEvent,
} from './api'
import { sampleCode } from './lib/sample'
import { supabase, supabaseEnabled } from './lib/supabase'
import type { Finding, Severity } from './types'

interface StreamProgress {
  scanned: number
  total: number
}

interface ScanState {
  code: string
  filename: string
  isScanning: boolean
  error: string | null
  result: ScanResponse | null
  severityFilter: Severity | 'all'
  typeFilter: string
  setCode: (code: string) => void
  setFilename: (filename: string) => void
  runScan: () => Promise<void>
  setSeverityFilter: (v: Severity | 'all') => void
  setTypeFilter: (v: string) => void
  reset: () => void

  streamFindings: Finding[]
  streamProgress: StreamProgress | null
  scanJobId: string | null
  runRepoScan: (url: string, branch?: string) => Promise<void>
  runZipScan: (file: File) => Promise<void>

  authEnabled: boolean
  userEmail: string | null
  token: string | null
  authReady: boolean
  isAuthOpen: boolean
  isHistoryOpen: boolean
  history: HistoricalScan[]
  historyLoading: boolean
  authError: string | null
  setAuthOpen: (open: boolean) => void
  setHistoryOpen: (open: boolean) => void
  initAuth: () => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  loadHistory: () => Promise<void>
  openScan: (scanId: string) => Promise<void>
  deleteHistoryScan: (scanId: string) => Promise<void>
}

type SetFn = (partial: Partial<ScanState> | ((s: ScanState) => Partial<ScanState>)) => void

function makeStreamHandlers(set: SetFn, job: ScanJob, fallbackFilename: string) {
  return {
    onEvent: (evt: ScanStreamEvent) => {
      if (evt.type === 'progress') {
        set({
          streamProgress: {
            scanned: evt.scanned ?? 0,
            total: evt.total ?? job.total_files,
          },
        })
      } else if (evt.type === 'file' && evt.findings?.length) {
        set((s) => ({ streamFindings: [...s.streamFindings, ...(evt.findings ?? [])] }))
      } else if (evt.type === 'snapshot' && evt.findings?.length) {
        set({ streamFindings: evt.findings })
      } else if (evt.type === 'done' && evt.findings) {
        set({
          result: {
            scan_id: evt.scan_id ?? job.scan_id,
            filename: evt.filename ?? fallbackFilename,
            total_issues: evt.total_issues ?? evt.findings.length,
            risk_score: evt.risk_score ?? 0,
            findings: evt.findings,
          },
          isScanning: false,
          scanJobId: null,
          streamProgress: null,
          streamFindings: [],
          severityFilter: 'all',
          typeFilter: 'all',
        })
      } else if (evt.type === 'failed') {
        set({
          error: evt.error ?? 'Scan failed',
          isScanning: false,
          scanJobId: null,
          streamProgress: null,
          streamFindings: [],
        })
      }
    },
    onEnd: () => {},
    onError: (msg: string) =>
      set((s) =>
        s.result
          ? {}
          : { error: msg, isScanning: false, streamProgress: null, scanJobId: null },
      ),
  }
}

function streamFrom(set: SetFn, job: ScanJob, fallbackFilename: string) {
  set({
    isScanning: true,
    error: null,
    result: null,
    scanJobId: job.scan_id,
    streamProgress: { scanned: 0, total: job.total_files },
    streamFindings: [],
  })
  subscribeScan(job.scan_id, makeStreamHandlers(set, job, fallbackFilename))
}

export const useScanStore = create<ScanState>((set, get) => ({
  code: sampleCode,
  filename: 'main.py',
  isScanning: false,
  error: null,
  result: null,
  severityFilter: 'all',
  typeFilter: 'all',
  setCode: (code) => set({ code }),
  setFilename: (filename) => set({ filename: filename || 'main.py' }),
  runScan: async () => {
    const { code, filename, token } = get()
    set({ isScanning: true, error: null })
    try {
      const job = await createScanJob({ code, filename }, token)
      streamFrom(set, job, filename)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Scan failed',
        isScanning: false,
      })
    }
  },
  setSeverityFilter: (severityFilter) => set({ severityFilter }),
  setTypeFilter: (typeFilter) => set({ typeFilter }),
  reset: () =>
    set({
      result: null,
      error: null,
      severityFilter: 'all',
      typeFilter: 'all',
      streamFindings: [],
      streamProgress: null,
      scanJobId: null,
    }),

  streamFindings: [],
  streamProgress: null,
  scanJobId: null,
  runRepoScan: async (url, branch) => {
    set({ isScanning: true, error: null })
    try {
      const job = await startRepoScan(url, branch, get().token)
      streamFrom(set, job, url)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Repo scan failed',
        isScanning: false,
      })
    }
  },
  runZipScan: async (file) => {
    set({ isScanning: true, error: null })
    try {
      const job = await startZipScan(file, get().token)
      streamFrom(set, job, file.name)
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Zip scan failed',
        isScanning: false,
      })
    }
  },

  authEnabled: supabaseEnabled(),
  userEmail: null,
  token: null,
  authReady: false,
  isAuthOpen: false,
  isHistoryOpen: false,
  history: [],
  historyLoading: false,
  authError: null,
  setAuthOpen: (isAuthOpen) => set({ isAuthOpen }),
  setHistoryOpen: (isHistoryOpen) => set({ isHistoryOpen }),
  initAuth: async () => {
    if (!supabase) {
      set({ authReady: true })
      return
    }
    const {
      data: { session },
    } = await supabase.auth.getSession()
    const token = session?.access_token ?? null
    set({ token, userEmail: session?.user.email ?? null, authReady: true })
    if (token) get().loadHistory()
    supabase.auth.onAuthStateChange((_event, s) => {
      set({ token: s?.access_token ?? null, userEmail: s?.user.email ?? null })
      if (s?.access_token) get().loadHistory()
    })
  },
  signIn: async (email, password) => {
    if (!supabase) return
    set({ authError: null })
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) set({ authError: error.message })
    else set({ isAuthOpen: false })
  },
  signUp: async (email, password) => {
    if (!supabase) return
    set({ authError: null })
    const { error } = await supabase.auth.signUp({ email, password })
    if (error) set({ authError: error.message })
    else {
      const { data } = await supabase.auth.getSession()
      if (data.session) set({ isAuthOpen: false })
      else set({ authError: 'Check your email for a confirmation link' })
    }
  },
  signOut: async () => {
    if (supabase) await supabase.auth.signOut()
    set({ token: null, userEmail: null, history: [], result: null, isHistoryOpen: false })
  },
  loadHistory: async () => {
    const { token } = get()
    if (!token) return
    set({ historyLoading: true })
    try {
      const { scans } = await listScans(token)
      set({ history: scans, historyLoading: false })
    } catch {
      set({ historyLoading: false })
    }
  },
  openScan: async (scanId) => {
    const { token } = get()
    if (!token) return
    const detail = await getHistoricalScan(token, scanId)
    set({
      result: {
        scan_id: detail.scan_id,
        filename: detail.filename,
        total_issues: detail.total_issues,
        risk_score: detail.risk_score,
        findings: detail.findings,
      },
      severityFilter: 'all',
      typeFilter: 'all',
      error: null,
    })
  },
  deleteHistoryScan: async (scanId) => {
    const { token } = get()
    if (!token) return
    await deleteHistoricalScan(token, scanId)
    set({ history: get().history.filter((h) => h.scan_id !== scanId) })
  },
}))