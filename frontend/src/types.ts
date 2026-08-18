export type Severity = 'Critical' | 'High' | 'Medium' | 'Low'

export interface Finding {
  type: string
  severity: Severity
  file: string
  line: number
  explanation: string
  suggested_fix?: string | null
  confidence: string
  source: string
  code_snippet?: string | null
}

export interface ScanResponse {
  scan_id?: string | null
  filename: string
  total_issues: number
  risk_score: number
  findings: Finding[]
}

export interface HistoricalScan {
  scan_id: string
  filename: string
  source_type: string
  total_issues: number
  risk_score: number
  created_at: string
}

export interface ScanDetail extends HistoricalScan {
  findings: Finding[]
}