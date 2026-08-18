import type { Finding, Severity } from '../types'

export const SEVERITY_ORDER: Severity[] = ['Critical', 'High', 'Medium', 'Low']

const RISK_WEIGHTS: Record<Severity, number> = {
  Critical: 10,
  High: 6,
  Medium: 3,
  Low: 1,
}

export function computeRiskScore(findings: Finding[]): number {
  const score = findings.reduce(
    (acc, f) => acc + (f.confidence === 'ai-suggested' ? 0 : RISK_WEIGHTS[f.severity]),
    0,
  )
  return Math.min(100, Math.max(0, score))
}

export function scoreColor(score: number): string {
  if (score >= 70) return '#ef4444'
  if (score >= 40) return '#f97316'
  if (score >= 15) return '#eab308'
  return '#3b82f6'
}

export const SEVERITY_STYLES: Record<Severity, { badge: string; dot: string; hex: string }> = {
  Critical: {
    badge: 'border-red-500/30 bg-red-500/15 text-red-400',
    dot: 'bg-red-500',
    hex: '#ef4444',
  },
  High: {
    badge: 'border-orange-500/30 bg-orange-500/15 text-orange-400',
    dot: 'bg-orange-500',
    hex: '#f97316',
  },
  Medium: {
    badge: 'border-yellow-500/30 bg-yellow-500/15 text-yellow-300',
    dot: 'bg-yellow-500',
    hex: '#eab308',
  },
  Low: {
    badge: 'border-blue-500/30 bg-blue-500/15 text-blue-400',
    dot: 'bg-blue-500',
    hex: '#3b82f6',
  },
}