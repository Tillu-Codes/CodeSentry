import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useScanStore } from '../store'
import { scoreColor, SEVERITY_ORDER, SEVERITY_STYLES } from '../lib/severity'

function AnimatedNumber({ value, color }: { value: number; color: string }) {
  const [display, setDisplay] = useState(value)

  useEffect(() => {
    let raf = 0
    const from = display
    const to = value
    const duration = 550
    const start = performance.now()
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      setDisplay(Math.round(from + (to - from) * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return <span style={{ color }}>{display}</span>
}

export default function RiskSummary() {
  const result = useScanStore((s) => s.result)
  if (!result) return null

  const data = SEVERITY_ORDER.map((sev) => ({
    name: sev,
    value: result.findings.filter((f) => f.severity === sev).length,
    color: SEVERITY_STYLES[sev].hex,
  })).filter((d) => d.value > 0)

  const score = result.risk_score
  const color = scoreColor(score)

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="flex items-center gap-4"
    >
      <div
        className="grid h-16 w-16 shrink-0 place-items-center rounded-full transition-shadow duration-500"
        style={{
          background: `conic-gradient(${color} ${score * 3.6}deg, #1e1e35 0deg)`,
          boxShadow: `0 0 22px ${color}33`,
        }}
      >
        <div className="grid h-[52px] w-[52px] place-items-center rounded-full bg-base-900">
          <AnimatedNumber value={score} color={color} />
        </div>
      </div>
      <div className="shrink-0">
        <div className="text-xs uppercase tracking-wider text-slate-500">Risk score</div>
        <div className="text-xs text-slate-500">weighted by severity · /100</div>
      </div>
      <div className="ml-auto h-24 w-36 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={30}
              outerRadius={44}
              paddingAngle={3}
              stroke="none"
            >
              {data.map((d) => (
                <Cell key={d.name} fill={d.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: '#161629',
                border: '1px solid #272748',
                borderRadius: 8,
                fontSize: 12,
              }}
              itemStyle={{ color: '#e2e8f0' }}
              formatter={(value, name) => [`${value} issue(s)`, String(name)]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}