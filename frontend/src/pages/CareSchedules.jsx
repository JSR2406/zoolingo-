import { useEffect, useState } from 'react'
import {
  Clock,
  Loader2,
  Plus,
  Trash2,
  X,
  Calendar,
  PawPrint,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const CATEGORIES = [
  { id: 'care', label: 'General Care', color: 'text-blue-400' },
  { id: 'feeding', label: 'Feeding', color: 'text-emerald-400' },
  { id: 'exercise', label: 'Exercise', color: 'text-green-400' },
  { id: 'medication', label: 'Medication', color: 'text-purple-400' },
  { id: 'grooming', label: 'Grooming', color: 'text-pink-400' },
  { id: 'hygiene', label: 'Hygiene', color: 'text-cyan-400' },
]

const FREQUENCIES = [
  { id: 'daily', label: 'Daily' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'biweekly', label: 'Biweekly' },
  { id: 'monthly', label: 'Monthly' },
  { id: 'quarterly', label: 'Quarterly' },
  { id: 'yearly', label: 'Yearly' },
]

const STATUS_COLORS = {
  due: 'bg-amber-500/10 text-amber-400',
  overdue: 'bg-red-500/10 text-red-400',
  upcoming: 'bg-emerald-500/10 text-emerald-400',
  inactive: 'bg-slate-500/10 text-slate-400',
}

function formatDate(value) {
  if (!value) return 'Not set'
  return new Date(value).toLocaleDateString()
}

function CareCard({ schedule, onToggle, onEdit, onDelete }) {
  const isOverdue = schedule.status === 'overdue'
  const isDue = schedule.status === 'due'

  return (
    <div
      className={`glass-panel rounded-xl p-4 relative overflow-hidden border ${isOverdue ? 'border-red-500/20' : 'border-transparent hover:border-primary/50'} transition-colors`}
    >
      {/* Left accent border */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${
        isOverdue ? 'bg-red-500' : isDue ? 'bg-amber-500' : 'bg-primary'
      }`} />
      
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-bold capitalize uppercase ${STATUS_COLORS[schedule.status]}`}>
              {schedule.status}
            </span>
            <span className={`text-xs ${CATEGORIES.find(c => c.id === schedule.category)?.color || 'text-muted'}`}>
              {CATEGORIES.find(c => c.id === schedule.category)?.label || schedule.category}
            </span>
          </div>
          <h3 className="font-semibold text-white truncate">{schedule.task}</h3>
          <p className="text-xs text-muted mt-0.5">
            {schedule.frequency.charAt(0).toUpperCase() + schedule.frequency.slice(1)} •
            {schedule.time_of_day ? new Date(`1970-01-01T${schedule.time_of_day}`).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Any time'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onToggle(schedule.id, !schedule.active)}
            className={`p-1.5 rounded bg-white/5 hover:bg-primary/10 text-white transition-colors`}
            title="Toggle active"
          >
            {schedule.active ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <X className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={() => onEdit(schedule)}
            className="p-1.5 rounded bg-white/5 hover:bg-white/10 text-text-secondary hover:text-white transition-colors"
            aria-label="Edit"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(schedule.id)}
            className="p-1.5 rounded bg-white/5 hover:bg-red-500/10 text-text-secondary hover:text-red-400 transition-colors"
            aria-label="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {schedule.next_due_on && (
        <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-xs">
          <span className="text-muted">Next due:</span>
          <span className="text-sm font-medium text-white">
            {new Date(schedule.next_due_on).toLocaleDateString()}
          </span>
        </div>
      )}
    </div>
  )
}

function CareForm({ schedule, onSave, onCancel }) {
  const [form, setForm] = useState({
    task: schedule?.task || '',
    category: schedule?.category || 'care',
    frequency: schedule?.frequency || 'daily',
    time_of_day: schedule?.time_of_day || '',
    next_due_on: schedule?.next_due_on ? schedule.next_due_on.slice(0, 10) : '',
    active: schedule?.active !== false,
  })

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const payload = {
      task: form.task.trim(),
      category: form.category,
      frequency: form.frequency,
      time_of_day: form.time_of_day,
      next_due_on: form.next_due_on || null,
      active: form.active,
    }

    try {
      const url = schedule?.id
        ? `${API_BASE}/api/petcare/care-schedules/${schedule.id}`
        : `${API_BASE}/api/petcare/care-schedules`
      const method = schedule?.id ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      const result = await res.json()
      onSave(result)
    } catch (err) {
      toast.error('Failed to save care schedule', err.message)
    }
  }

  const toast = useToast()

  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-white">{schedule ? 'Edit Care Schedule' : 'Add Care Schedule'}</h2>
        <button onClick={onCancel} className="rounded-lg p-2 text-muted hover:bg-white/10 hover:text-white transition-colors">
          <X className="w-5 h-5" />
        </button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs text-muted uppercase tracking-wider">Task Name</label>
            <input
              className={inputClass}
              value={form.task}
              onChange={(e) => updateField('task', e.target.value)}
              placeholder="e.g. Evening walk"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted uppercase tracking-wider">Category</label>
            <select
              className={inputClass}
              value={form.category}
              onChange={(e) => updateField('category', e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c.id} value={c.id} className="bg-neutral-900">
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted uppercase tracking-wider">Frequency</label>
            <select
              className={inputClass}
              value={form.frequency}
              onChange={(e) => updateField('frequency', e.target.value)}
            >
              {FREQUENCIES.map((f) => (
                <option key={f.id} value={f.id} className="bg-neutral-900">
                  {f.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted uppercase tracking-wider">Time of Day</label>
            <input
              type="time"
              className={inputClass}
              value={form.time_of_day}
              onChange={(e) => updateField('time_of_day', e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-muted uppercase tracking-wider">Next Due Date</label>
            <input
              type="date"
              className={inputClass}
              value={form.next_due_on}
              onChange={(e) => updateField('next_due_on', e.target.value)}
            />
          </div>
          <div className="sm:col-span-2 flex items-center gap-2">
            <input
              id="active"
              type="checkbox"
              className="w-4 h-4 rounded bg-white/5 border border-white/10 text-primary focus:ring-primary"
              checked={form.active}
              onChange={(e) => updateField('active', e.target.checked)}
            />
            <label htmlFor="active" className="text-sm text-white">
              Active task
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-text-secondary hover:bg-white/10 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
          >
            {schedule ? 'Save Changes' : 'Add Schedule'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default function CareSchedules() {
  const toast = useToast()
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/petcare/care-schedules`)
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (!cancelled) setSchedules(data)
      } catch (err) {
        if (!cancelled) {
          // Fallback demo data
          setSchedules([
            {
              id: 1,
              task: 'Evening walk',
              category: 'exercise',
              frequency: 'daily',
              time_of_day: '18:00',
              next_due_on: new Date().toISOString().split('T')[0],
              active: true,
              status: 'due',
            },
            {
              id: 2,
              task: 'Heartworm prevention',
              category: 'medication',
              frequency: 'monthly',
              time_of_day: '08:00',
              next_due_on: new Date(Date.now() + 86400000 * 15).toISOString().split('T')[0],
              active: true,
              status: 'upcoming',
            },
            {
              id: 3,
              task: 'Litter box clean',
              category: 'hygiene',
              frequency: 'daily',
              time_of_day: '07:30',
              next_due_on: new Date(Date.now() - 86400000).toISOString().split('T')[0],
              active: true,
              status: 'overdue',
            },
          ])
          toast.info('Using demo data', 'Backend not reachable — showing sample schedules')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const handleToggle = async (id, isActive) => {
    try {
      const res = await fetch(`${API_BASE}/api/petcare/care-schedules/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: isActive }),
      })
      if (!res.ok) throw new Error('Failed to update')
      const result = await res.json()
      setSchedules((prev) =>
        prev.map((s) => (s.id === id ? result : s))
      )
    } catch (err) {
      toast.error('Failed to update schedule', err.message)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this care schedule?')) return
    try {
      const res = await fetch(`${API_BASE}/api/petcare/care-schedules/${id}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete')
      setSchedules((prev) => prev.filter((s) => s.id !== id))
    } catch (err) {
      toast.error('Failed to delete schedule', err.message)
    }
  }

  const startAdd = () => {
    setEditingSchedule(null)
    setShowForm(true)
  }

  const startEdit = (schedule) => {
    setEditingSchedule(schedule)
    setShowForm(true)
  }

  const cancelForm = () => {
    setShowForm(false)
    setEditingSchedule(null)
  }

  const handleSave = (savedSchedule) => {
    setSchedules((prev) =>
      editingSchedule
        ? prev.map((s) => (s.id === savedSchedule.id ? savedSchedule : s))
        : [savedSchedule, ...prev]
    )
    setShowForm(false)
    setEditingSchedule(null)
  }

  const statusCounts = schedules.reduce(
    (acc, s) => {
      acc[s.status] = (acc[s.status] || 0) + 1
      return acc
    },
    { due: 0, overdue: 0, upcoming: 0, inactive: 0 }
  )

  return (
    <div className="space-y-6">
      <header className="glass-panel-solid rounded-xl p-6">
        <div className="flex items-center gap-3">
          <CalendarClock className="h-6 w-6 text-primary" />
          <h1 className="font-display text-2xl font-bold gradient-text">Care Schedules</h1>
        </div>
        <p className="mt-1 text-text-secondary">
          Track feeding, medication, exercise, and grooming routines for your pets.
        </p>
      </header>
      <div className="grid gap-4 sm:grid-cols-4">
        <div className="glass-panel rounded-xl p-4">
          <div className="text-xs text-muted uppercase tracking-wider font-semibold">Overdue</div>
          <div className="text-2xl font-bold text-red-400">{statusCounts.overdue}</div>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <div className="text-xs text-muted uppercase tracking-wider font-semibold">Due Soon</div>
          <div className="text-2xl font-bold text-amber-400">{statusCounts.due}</div>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <div className="text-xs text-muted uppercase tracking-wider font-semibold">Upcoming</div>
          <div className="text-2xl font-bold text-emerald-400">{statusCounts.upcoming}</div>
        </div>
        <div className="glass-panel rounded-xl p-4">
          <div className="text-xs text-muted uppercase tracking-wider font-semibold">Total</div>
          <div className="text-2xl font-bold text-white">{schedules.length}</div>
        </div>
      </div>

      {showForm ? (
        <CareForm schedule={editingSchedule} onSave={handleSave} onCancel={cancelForm} />
      ) : null}

      <div className="flex items-center justify-between mb-4">
        <h2 className="font-bold text-white">Upcoming Tasks</h2>
        <button
          onClick={startAdd}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          <Plus className="h-4 w-4" /> Add Schedule
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-text-secondary">Loading schedules...</p>
        </div>
      ) : schedules.length === 0 ? (
        <div className="glass-panel rounded-xl p-8 text-center">
          <div className="text-3xl mb-3">📋</div>
          <h3 className="font-bold text-white mb-2">No care schedules yet</h3>
          <p className="text-sm text-muted">Add your first care task to start tracking routines.</p>
          <button
            onClick={startAdd}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            <Plus className="h-4 w-4" /> Create Schedule
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((schedule) => (
            <CareCard
              key={schedule.id}
              schedule={schedule}
              onToggle={handleToggle}
              onEdit={startEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}
