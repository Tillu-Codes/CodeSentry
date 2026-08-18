import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Filter } from 'lucide-react'
import { useScanStore } from '../store'
import { SEVERITY_ORDER, SEVERITY_STYLES } from '../lib/severity'
import type { Severity } from '../types'

function Chip({
  active,
  onClick,
  dot,
  children,
}: {
  active: boolean
  onClick: () => void
  dot?: string
  children: React.ReactNode
}) {
  return (
    <motion.button
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
        active
          ? 'border-violet-500/50 bg-violet-500/15 text-violet-200'
          : 'border-white/10 bg-base-800 text-slate-400 hover:bg-base-700 hover:text-slate-200'
      }`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />}
      {children}
    </motion.button>
  )
}

export default function FilterBar() {
  const result = useScanStore((s) => s.result)
  const severityFilter = useScanStore((s) => s.severityFilter)
  const typeFilter = useScanStore((s) => s.typeFilter)
  const setSeverityFilter = useScanStore((s) => s.setSeverityFilter)
  const setTypeFilter = useScanStore((s) => s.setTypeFilter)

  const types = useMemo(
    () => (result ? [...new Set<string>(result.findings.map((f) => f.type))].sort() : []),
    [result],
  )

  return (
    <div className="mt-3 flex flex-wrap items-center gap-1.5">
      <Filter size={13} className="mr-1 text-slate-600" />
      <Chip active={severityFilter === 'all'} onClick={() => setSeverityFilter('all')}>
        All
      </Chip>
      {SEVERITY_ORDER.map((sev: Severity) => (
        <Chip
          key={sev}
          active={severityFilter === sev}
          onClick={() => setSeverityFilter(sev)}
          dot={SEVERITY_STYLES[sev].dot}
        >
          {sev}
        </Chip>
      ))}
      <select
        value={typeFilter}
        onChange={(e) => setTypeFilter(e.target.value)}
        className="ml-auto max-w-[200px] rounded-lg border border-white/10 bg-base-800 px-2 py-1 text-xs text-slate-300 outline-none focus:border-violet-500/50"
      >
        <option value="all">All types</option>
        {types.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
    </div>
  )
}