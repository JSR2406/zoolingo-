import { Brain } from 'lucide-react'

export default function Expert() {
  return (
    <div className="glass-panel rounded-xl p-6">
      <div className="flex h-40 flex-col items-center justify-center gap-3 text-center">
        <Brain className="h-10 w-10 text-primary" />
        <h2 className="text-2xl font-bold gradient-text">Pet Care Expert</h2>
        <p className="text-sm text-text-secondary">AI pet care advice coming soon.</p>
      </div>
    </div>
  )
}