import { CalendarClock } from 'lucide-react'

export default function CareSchedules() {
  return (
    <div className="glass-panel rounded-xl p-6">
      <div className="flex h-40 flex-col items-center justify-center gap-3 text-center">
        <CalendarClock className="h-10 w-10 text-primary" />
        <h2 className="text-2xl font-bold gradient-text">Care Schedules</h2>
        <p className="text-sm text-text-secondary">Feeding and care reminders coming soon.</p>
      </div>
    </div>
  )
}