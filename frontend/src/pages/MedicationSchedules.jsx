import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  X,
  Pill,
  AlertCircle,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

function statusChip(status) {
  if (status === 'overdue') {
    return (
      <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
        Overdue
      </span>
    )
  }
  if (status === 'due') {
    return (
      <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">
        Due soon
      </span>
    )
  }
  if (status === 'inactive') {
    return (
      <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary">
        Inactive
      </span>
    )
  }
  return (
    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary">
      Upcoming
    </span>
  )
}

export default function MedicationSchedules() {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)
  const [newMed, setNewMed] = useState({
    pet_id: '',
    medication_name: '',
    dosage: '',
    frequency: 'daily',
    time_of_day: '',
    next_due_on: '',
    active: true,
  })
  const [editingId, setEditingId] = useState(null)
  const toast = useToast()

  const fetchSchedules = async () => {
    const res = await fetch(`${API_BASE}/api/petcare/medication-schedules`)
    const data = await res.json()
    setSchedules(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchSchedules()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    const res = await fetch(`${API_BASE}/api/petcare/medication-schedules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...newMed,
        active: newMed.active === true || newMed.active === 'true',
        next_due_on: newMed.next_due_on || null,
      }),
    })
    if (res.ok) {
      setNewMed({
        pet_id: '',
        medication_name: '',
        dosage: '',
        frequency: 'daily',
        time_of_day: '',
        next_due_on: '',
        active: true,
      })
      await fetchSchedules()
      toast.success('Created', 'Medication schedule added')
    } else {
      toast.error('Error', 'Failed to create medication schedule')
    }
  }

  const handleToggle = async (id, currentActive) => {
    const res = await fetch(
      `${API_BASE}/api/petcare/medication-schedules/${id}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !currentActive }),
      },
    )
    if (res.ok) await fetchSchedules()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this medication schedule?')) return
    const res = await fetch(
      `${API_BASE}/api/petcare/medication-schedules/${id}`,
      { method: 'DELETE' },
    )
    if (res.ok) {
      await fetchSchedules()
      toast.success('Deleted', 'Medication schedule removed')
    }
  }

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-10 h-10 animate-spin text-primary mb-4" />
        <p className="text-text-secondary">Loading medication schedules...</p>
      </div>
    )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">Medication Schedules</h1>
        <Pill className="w-5 h-5 text-primary" />
      </div>

      <p className="text-text-secondary">
        Track medications, dosages, and refill reminders for your pets.
      </p>

      <form onSubmit={handleCreate} className="glass-panel-solid rounded-3xl p-6 space-y-4">
        <h3 className="font-semibold text-text-primary">Add Medication Schedule</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Pet ID
            </label>
            <input
              className={inputClass}
              value={newMed.pet_id}
              onChange={(e) =>
                setNewMed({ ...newMed, pet_id: e.target.value })
              }
              placeholder="e.g. 1"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Medication Name
            </label>
            <input
              className={inputClass}
              value={newMed.medication_name}
              onChange={(e) =>
                setNewMed({
                  ...newMed,
                  medication_name: e.target.value,
                })
              }
              placeholder="e.g. Heartgard"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Dosage
            </label>
            <input
              className={inputClass}
              value={newMed.dosage}
              onChange={(e) =>
                setNewMed({ ...newMed, dosage: e.target.value })
              }
              placeholder="e.g. 1 chewable"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Frequency
            </label>
            <select
              className={inputClass}
              value={newMed.frequency}
              onChange={(e) =>
                setNewMed({ ...newMed, frequency: e.target.value })
              }
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="as_needed">As Needed</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Time of Day
            </label>
            <input
              className={inputClass}
              type="time"
              value={newMed.time_of_day}
              onChange={(e) =>
                setNewMed({ ...newMed, time_of_day: e.target.value })
              }
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Next Due Date
            </label>
            <input
              className={inputClass}
              type="date"
              value={newMed.next_due_on}
              onChange={(e) =>
                setNewMed({ ...newMed, next_due_on: e.target.value })
              }
            />
          </div>
          <div className="flex items-center">
            <input
              className="w-4 h-4 rounded bg-white/5 border border-white/10 text-primary focus:ring-primary"
              type="checkbox"
              checked={newMed.active}
              onChange={(e) =>
                setNewMed({ ...newMed, active: e.target.checked })
              }
            />
            <label className="ml-2 text-text-secondary">
              Active
            </label>
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Add Schedule
            </button>
          </div>
        </div>
      </form>

      <div className="glass-panel-solid rounded-3xl p-6">
        <h3 className="font-semibold text-text-primary mb-4">
          Your Medication Schedules
        </h3>
        {schedules.length === 0 ? (
          <div className="text-center py-8 text-text-muted">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No medication schedules yet. Add one above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {schedules.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">
                      {s.medication_name}
                    </span>
                    <span className="text-xs text-text-muted">
                      Pet #{s.pet_id}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-text-secondary mt-1">
                    <span>{s.dosage}</span>
                    <span>•</span>
                    <span>{s.frequency}</span>
                    <span>•</span>
                    <span>{s.time_of_day || '—'}</span>
                    <span>•</span>
                    <span>{s.next_due_on || '—'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {statusChip(s.active ? 'upcoming' : 'inactive')}
                  <button
                    onClick={() => handleToggle(s.id, s.active)}
                    className="p-2 rounded hover:bg-white/10 text-text-secondary hover:text-primary transition-colors"
                  >
                    {s.active ? 'Pause' : 'Resume'}
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="p-2 rounded hover:bg-red-500/10 text-red-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
