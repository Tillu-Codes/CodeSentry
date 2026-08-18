import { useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, ArrowLeft, Loader2, Radio, Sparkles } from 'lucide-react'
import { useScanStore } from '../store'
import FindingCard from './FindingCard'
import FilterBar from './FilterBar'
import RiskScene3D from './RiskScene3D'
import RiskSummary from './RiskSummary'
import { Button } from './ui'

function StreamingView() {
  const streamProgress = useScanStore((s) => s.streamProgress)
  const streamFindings = useScanStore((s) => s.streamFindings)
  const pct = streamProgress && streamProgress.total > 0
    ? Math.round((streamProgress.scanned / streamProgress.total) * 100)
    : 0

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35 }}
      className="relative flex min-h-0 flex-1 flex-col"
    >
      <div className="relative h-[260px] shrink-0 overflow-hidden border-b border-white/5">
        <RiskScene3D />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-base-950/70 to-transparent" />
        <div className="absolute left-4 top-3 flex items-center gap-2 rounded-full border border-violet-500/30 bg-base-900/70 px-3 py-1 text-xs text-violet-300 backdrop-blur">
          <Radio size={12} className="animate-pulse" />
          Streaming findings in real time
        </div>
        <div className="absolute bottom-3 right-4 flex items-center gap-2 rounded-full border border-white/10 bg-base-900/70 px-3 py-1.5 text-xs backdrop-blur">
          <span className="text-slate-300">{streamFindings.length} finding(s)</span>
          <span className="text-slate-500">
            {streamProgress ? `${streamProgress.scanned}/${streamProgress.total} files` : '…'}
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 py-8">
        <Loader2 size={22} className="animate-spin text-violet-400" />
        <div className="h-1.5 w-64 overflow-hidden rounded-full bg-base-800">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
        <p className="text-sm text-slate-500">
          Analyzing {streamProgress ? `${streamProgress.scanned} of ${streamProgress.total}` : '…'} files…
        </p>
      </div>
    </motion.div>
  )
}

export default function ResultsPanel({ onBack }: { onBack: () => void }) {
  const result = useScanStore((s) => s.result)
  const isScanning = useScanStore((s) => s.isScanning)
  const error = useScanStore((s) => s.error)
  const severityFilter = useScanStore((s) => s.severityFilter)
  const typeFilter = useScanStore((s) => s.typeFilter)
  const reset = useScanStore((s) => s.reset)

  const findings = useMemo(() => {
    if (!result) return []
    return result.findings.filter(
      (f) =>
        (severityFilter === 'all' || f.severity === severityFilter) &&
        (typeFilter === 'all' || f.type === typeFilter),
    )
  }, [result, severityFilter, typeFilter])

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="grid flex-1 place-items-center p-6"
      >
        <div className="max-w-sm rounded-xl border border-red-500/20 bg-red-500/5 p-5 text-center">
          <AlertTriangle className="mx-auto mb-2 text-red-400" size={22} />
          <p className="text-sm text-red-300">{error}</p>
          <Button
            className="mt-4 border border-white/10 bg-base-800 text-slate-200 hover:bg-base-700"
            onClick={reset}
          >
            Try again
          </Button>
        </div>
      </motion.div>
    )
  }

  if (!result) {
    if (isScanning) {
      return <StreamingView />
    }
    return (
      <div className="grid flex-1 place-items-center p-6">
        <div className="text-center text-slate-600">
          <Sparkles className="mx-auto mb-3 text-violet-500/60" size={30} />
          <p className="text-sm">Paste Python code, a GitHub repo, or a zip archive and hit Analyze.</p>
          <p className="mt-1 text-xs text-slate-700">
            Findings, risk score and a 3D visualization will appear here in real time.
          </p>
          <Button
            className="mt-5 border border-white/10 bg-base-800 text-slate-300 hover:bg-base-700 lg:hidden"
            onClick={onBack}
          >
            <ArrowLeft size={14} /> Back to editor
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-white/5 bg-base-900/50 px-4 py-3">
        <div className="mb-3 flex items-center justify-between">
          <motion.h2
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-sm font-semibold text-white"
          >
            Scan results
          </motion.h2>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-slate-500">
              {result.filename} · {result.total_issues} issues
            </span>
            <Button
              className="h-7 border border-white/10 bg-base-800 px-2 text-xs text-slate-300 hover:bg-base-700 lg:hidden"
              onClick={onBack}
            >
              Back
            </Button>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="relative mb-3 h-44 overflow-hidden rounded-xl border border-white/5"
        >
          <RiskScene3D />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-base-950/60 to-transparent" />
        </motion.div>

        <RiskSummary />
        <FilterBar />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {findings.length === 0 ? (
          <div className="grid place-items-center py-12 text-sm text-slate-600">
            No findings match the current filters.
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {findings.map((f, i) => (
              <FindingCard
                key={`${f.source}-${f.line}-${f.type}`}
                finding={f}
                delay={Math.min(i * 0.035, 0.45)}
              />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}