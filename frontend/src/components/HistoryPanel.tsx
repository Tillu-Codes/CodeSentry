import { useEffect } from 'react'
import { Clock, Loader2, Trash2, X } from 'lucide-react'
import { useScanStore } from '../store'
import { scoreColor } from '../lib/severity'
import { Button } from './ui'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return new Date(iso).toLocaleDateString()
}

export default function HistoryPanel() {
  const {
    isHistoryOpen,
    setHistoryOpen,
    history,
    historyLoading,
    loadHistory,
    openScan,
    deleteHistoryScan,
  } = useScanStore()

  useEffect(() => {
    if (isHistoryOpen) loadHistory()
  }, [isHistoryOpen, loadHistory])

  if (!isHistoryOpen) return null

  return (
    <div
      className="fixed inset-0 z-40 grid place-items-center bg-black/60 backdrop-blur-sm"
      onClick={() => setHistoryOpen(false)}
    >
      <div
        className="flex max-h-[80vh] w-full max-w-lg flex-col rounded-2xl border border-white/10 bg-base-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
          <div className="flex items-center gap-2">
            <Clock size={17} className="text-violet-400" />
            <h2 className="text-base font-bold text-white">Scan history</h2>
          </div>
          <button
            onClick={() => setHistoryOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:text-white"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 py-2">
          {historyLoading ? (
            <div className="grid place-items-center py-10 text-slate-400">
              <Loader2 className="animate-spin" size={22} />
            </div>
          ) : history.length === 0 ? (
            <div className="px-2 py-10 text-center text-sm text-slate-500">
              No saved scans yet. Sign in and run a scan to save it to your history.
            </div>
          ) : (
            <ul className="divide-y divide-white/5">
              {history.map((h) => (
                <li key={h.scan_id} className="flex items-center gap-3 py-2.5">
                  <button
                    onClick={() => openScan(h.scan_id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="truncate text-sm font-medium text-slate-200">
                      {h.filename || h.source_type}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="capitalize">{h.source_type}</span>
                      <span>·</span>
                      <span>{h.total_issues} issues</span>
                      <span>·</span>
                      <span>{timeAgo(h.created_at)}</span>
                    </div>
                  </button>
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: scoreColor(h.risk_score) }}
                    title={`Risk ${h.risk_score}/100`}
                  />
                  <Button
                    onClick={() => deleteHistoryScan(h.scan_id)}
                    className="shrink-0 p-1.5 text-slate-500 hover:text-red-400"
                    aria-label="Delete scan"
                  >
                    <Trash2 size={15} />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}