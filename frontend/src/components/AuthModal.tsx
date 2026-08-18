import { useEffect, useState } from 'react'
import { Loader2, LogIn, X } from 'lucide-react'
import { useScanStore } from '../store'
import { Button } from './ui'

type Mode = 'signin' | 'signup'

export default function AuthModal() {
  const { isAuthOpen, setAuthOpen, signIn, signUp, authError, authEnabled } = useScanStore()
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (isAuthOpen) {
      setEmail('')
      setPassword('')
      setMode('signin')
    }
  }, [isAuthOpen])

  if (!isAuthOpen || !authEnabled) return null

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      if (mode === 'signin') await signIn(email, password)
      else await signUp(email, password)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm"
      onClick={() => setAuthOpen(false)}
    >
      <div
        className="w-full max-w-sm rounded-2xl border border-white/10 bg-base-800 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {mode === 'signin' ? 'Sign in' : 'Create account'}
          </h2>
          <button
            onClick={() => setAuthOpen(false)}
            className="rounded-md p-1 text-slate-400 hover:text-white"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-lg border border-white/10 bg-base-950 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-violet-500 focus:outline-none"
          />
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="w-full rounded-lg border border-white/10 bg-base-950 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-violet-500 focus:outline-none"
          />

          {authError && (
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              {authError}
            </div>
          )}

          <Button
            type="submit"
            disabled={busy}
            className="w-full bg-gradient-to-r from-violet-500 to-indigo-600 text-white hover:from-violet-400 hover:to-indigo-500"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : <LogIn size={15} />}
            {mode === 'signin' ? 'Sign in' : 'Sign up'}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">
          {mode === 'signin' ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            onClick={() => setMode(mode === 'signin' ? 'signup' : 'signin')}
            className="font-semibold text-violet-400 hover:text-violet-300"
          >
            {mode === 'signin' ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  )
}