import { useEffect, useState } from 'react'
import { Clock, LogOut, ShieldCheck, UserRound } from 'lucide-react'
import { checkHealth } from '../api'
import { useScanStore } from '../store'

interface HeaderProps {
  view: 'editor' | 'results'
  onViewChange: (v: 'editor' | 'results') => void
}

export default function Header({ view, onViewChange }: HeaderProps) {
  const [online, setOnline] = useState<boolean | null>(null)
  const { authEnabled, authReady, userEmail, setAuthOpen, setHistoryOpen, signOut } =
    useScanStore()

  useEffect(() => {
    let alive = true
    checkHealth().then((ok) => {
      if (alive) setOnline(ok)
    })
    return () => {
      alive = false
    }
  }, [])

  return (
    <header className="flex items-center justify-between border-b border-white/5 bg-base-900/60 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-2.5">
        <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-indigo-700 text-white shadow-lg shadow-violet-900/40">
          <ShieldCheck size={18} />
        </div>
        <div>
          <div className="text-base font-bold tracking-tight text-white">
            Code
            <span className="bg-gradient-to-r from-violet-400 to-indigo-300 bg-clip-text text-transparent">
              Sentry
            </span>
          </div>
          <div className="text-[11px] text-slate-500">Python bug &amp; security scanner</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span
          className={`hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs sm:inline-flex ${
            online === null
              ? 'border-white/10 bg-base-800 text-slate-400'
              : online
                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                : 'border-red-500/20 bg-red-500/10 text-red-400'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              online === null ? 'bg-slate-500' : online ? 'animate-pulse bg-emerald-400' : 'bg-red-400'
            }`}
          />
          {online === null ? 'checking API…' : online ? 'API online' : 'API offline'}
        </span>

        <div className="flex rounded-lg border border-white/10 bg-base-800 p-0.5 lg:hidden">
          {(['editor', 'results'] as const).map((v) => (
            <button
              key={v}
              onClick={() => onViewChange(v)}
              className={`rounded-md px-3 py-1 text-xs font-medium capitalize transition-colors ${
                view === v ? 'bg-base-600 text-white' : 'text-slate-400'
              }`}
            >
              {v}
            </button>
          ))}
        </div>

        {authEnabled && authReady && (
          <>
            {userEmail ? (
              <>
                <button
                  onClick={() => setHistoryOpen(true)}
                  className="hidden items-center gap-1.5 rounded-lg border border-white/10 bg-base-800 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-base-700 sm:inline-flex"
                  title="Scan history"
                >
                  <Clock size={14} className="text-violet-400" />
                  History
                </button>
                <div className="hidden items-center gap-2 sm:flex">
                  <span
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-base-800 px-2.5 py-1 text-xs text-slate-300"
                    title={userEmail}
                  >
                    <UserRound size={13} className="text-violet-400" />
                    <span className="max-w-32 truncate">{userEmail}</span>
                  </span>
                  <button
                    onClick={() => signOut()}
                    className="rounded-lg border border-white/10 bg-base-800 p-1.5 text-slate-400 transition-colors hover:text-white"
                    title="Sign out"
                  >
                    <LogOut size={14} />
                  </button>
                </div>
              </>
            ) : (
              <button
                onClick={() => setAuthOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-semibold text-violet-300 transition-colors hover:bg-violet-500/20"
              >
                <UserRound size={14} />
                Sign in
              </button>
            )}
          </>
        )}
      </div>
    </header>
  )
}