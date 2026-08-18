import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Brain, Check, ChevronDown, Copy } from 'lucide-react'
import type { Finding } from '../types'
import { SEVERITY_STYLES } from '../lib/severity'
import { Badge } from './ui'

export default function FindingCard({
  finding,
  delay = 0,
}: {
  finding: Finding
  delay?: number
}) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const styles = SEVERITY_STYLES[finding.severity]

  const copyFix = async () => {
    if (!finding.suggested_fix) return
    await navigator.clipboard.writeText(finding.suggested_fix).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10, scale: 0.99 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ duration: 0.2, delay }}
      className={`mb-2 overflow-hidden rounded-xl border bg-base-900/60 transition-colors ${
        open ? 'border-white/15' : 'border-white/5'
      }`}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
      >
        <span className={`h-2 w-2 shrink-0 rounded-full ${styles.dot}`} />
        <Badge className={styles.badge}>{finding.severity}</Badge>
        <span className="min-w-0 flex-1 truncate font-mono text-[13px] font-medium text-slate-200">
          {finding.type}
        </span>
        <span className="hidden shrink-0 font-mono text-xs text-slate-500 sm:inline">
          {finding.file}:{finding.line}
        </span>
        {finding.confidence === 'ai-suggested' && (
          <Brain size={13} className="shrink-0 text-violet-400" aria-label="AI-suggested" />
        )}
        <ChevronDown
          size={16}
          className={`shrink-0 text-slate-500 transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-3 border-t border-white/5 px-4 py-3">
              {finding.code_snippet && (
                <pre className="overflow-x-auto rounded-lg border border-white/5 bg-base-950/80 px-3 py-2 font-mono text-xs leading-relaxed text-slate-400">
                  {finding.code_snippet}
                </pre>
              )}
              <p className="text-sm leading-relaxed text-slate-300">{finding.explanation}</p>
              {finding.suggested_fix && (
                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-500">Suggested fix</span>
                    <button
                      onClick={copyFix}
                      className="flex items-center gap-1.5 rounded-md border border-white/10 bg-base-800 px-2 py-1 text-xs text-slate-300 transition-colors hover:bg-base-700"
                    >
                      {copied ? (
                        <Check size={12} className="text-emerald-400" />
                      ) : (
                        <Copy size={12} />
                      )}
                      {copied ? 'Copied' : 'Copy fix'}
                    </button>
                  </div>
                  <pre className="overflow-x-auto rounded-lg border border-violet-500/20 bg-violet-500/5 px-3 py-2 font-mono text-xs leading-relaxed text-violet-200">
                    {finding.suggested_fix}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}