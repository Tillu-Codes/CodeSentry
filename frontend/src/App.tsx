import { useEffect, useState } from 'react'
import Header from './components/Header'
import CodeInput from './components/CodeInput'
import ResultsPanel from './components/ResultsPanel'
import AuthModal from './components/AuthModal'
import HistoryPanel from './components/HistoryPanel'
import { useScanStore } from './store'

export default function App() {
  const [view, setView] = useState<'editor' | 'results'>('editor')
  const initAuth = useScanStore((s) => s.initAuth)

  useEffect(() => {
    initAuth()
  }, [initAuth])

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-base-950 text-slate-200">
      <Header view={view} onViewChange={setView} />
      <main className="flex min-h-0 flex-1">
        <section
          className={`${view === 'editor' ? 'flex' : 'hidden'} w-full flex-col lg:flex lg:w-1/2`}
        >
          <CodeInput />
        </section>
        <section
          className={`${view === 'results' ? 'flex' : 'hidden'} w-full flex-col border-t border-white/5 lg:flex lg:flex-1 lg:border-l lg:border-t-0`}
        >
          <ResultsPanel onBack={() => setView('editor')} />
        </section>
      </main>
      <AuthModal />
      <HistoryPanel />
    </div>
  )
}