import { useState } from 'react'
import Editor from '@monaco-editor/react'
import { motion } from 'framer-motion'
import { FileArchive, FileCode2, GitBranch, Loader2, Play } from 'lucide-react'
import { useScanStore } from '../store'
import { Button } from './ui'

type Mode = 'snippet' | 'repo' | 'zip'

const TABS: { id: Mode; label: string; icon: typeof FileCode2 }[] = [
  { id: 'snippet', label: 'Snippet', icon: FileCode2 },
  { id: 'repo', label: 'GitHub', icon: GitBranch },
  { id: 'zip', label: 'ZIP', icon: FileArchive },
]

export default function CodeInput() {
  const code = useScanStore((s) => s.code)
  const filename = useScanStore((s) => s.filename)
  const isScanning = useScanStore((s) => s.isScanning)
  const setCode = useScanStore((s) => s.setCode)
  const setFilename = useScanStore((s) => s.setFilename)
  const runScan = useScanStore((s) => s.runScan)
  const runRepoScan = useScanStore((s) => s.runRepoScan)
  const runZipScan = useScanStore((s) => s.runZipScan)

  const [mode, setMode] = useState<Mode>('snippet')
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [zipFile, setZipFile] = useState<File | null>(null)

  const canRun =
    !isScanning &&
    (mode === 'snippet'
      ? code.trim().length > 0
      : mode === 'repo'
        ? repoUrl.trim().length > 0
        : zipFile !== null)

  const run = () => {
    if (mode === 'snippet') void runScan()
    else if (mode === 'repo') void runRepoScan(repoUrl.trim(), branch.trim() || undefined)
    else if (zipFile) void runZipScan(zipFile)
  }

  const runLabel = isScanning
    ? 'Scanning…'
    : mode === 'snippet'
      ? 'Analyze'
      : mode === 'repo'
        ? 'Scan repo'
        : 'Scan zip'

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-white/5 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex rounded-lg border border-white/10 bg-base-800 p-0.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setMode(id)}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  mode === id ? 'bg-base-600 text-white' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </div>
          {mode === 'snippet' && (
            <input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              aria-label="Filename"
              className="w-36 rounded-md border border-white/10 bg-base-800 px-2 py-1 font-mono text-xs text-slate-300 outline-none focus:border-violet-500/50"
            />
          )}
        </div>
        <motion.div whileTap={canRun ? { scale: 0.96 } : undefined}>
          <Button
            onClick={run}
            disabled={!canRun}
            className="bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-lg shadow-violet-900/30 hover:from-violet-500 hover:to-indigo-500"
          >
            {isScanning ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
            {runLabel}
          </Button>
        </motion.div>
      </div>

      <div className="min-h-0 flex-1">
        {mode === 'snippet' ? (
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(v) => setCode(v ?? '')}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
              scrollBeyondLastLine: false,
              padding: { top: 12 },
              tabSize: 4,
              automaticLayout: true,
            }}
          />
        ) : (
          <div className="grid h-full place-items-center p-6">
            <div className="w-full max-w-md space-y-4">
              {mode === 'repo' ? (
                <>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">
                      GitHub repository URL
                    </label>
                    <input
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      placeholder="https://github.com/owner/repo"
                      className="w-full rounded-lg border border-white/10 bg-base-800 px-3 py-2 font-mono text-sm text-slate-200 outline-none placeholder:text-slate-500 focus:border-violet-500/50"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">
                      Branch (optional)
                    </label>
                    <input
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      placeholder="main"
                      className="w-full rounded-lg border border-white/10 bg-base-800 px-3 py-2 font-mono text-sm text-slate-200 outline-none placeholder:text-slate-500 focus:border-violet-500/50"
                    />
                  </div>
                  <p className="text-xs leading-relaxed text-slate-500">
                    Fetches the repo tree and streams each file&apos;s findings to the results panel
                    as they are scanned. Files are fetched in parallel and rate-limited by GitHub.
                  </p>
                </>
              ) : (
                <>
                  <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-white/15 bg-base-800/60 px-6 py-10 text-center transition-colors hover:border-violet-500/40 hover:bg-base-800">
                    <FileArchive size={28} className="text-violet-400" />
                    <span className="text-sm font-medium text-slate-300">
                      {zipFile ? zipFile.name : 'Choose a .zip archive'}
                    </span>
                    <span className="text-xs text-slate-500">
                      Any zip containing .py files
                    </span>
                    <input
                      type="file"
                      accept=".zip,application/zip"
                      className="hidden"
                      onChange={(e) => setZipFile(e.target.files?.[0] ?? null)}
                    />
                  </label>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}