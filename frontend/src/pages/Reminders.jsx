import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  Clock,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

function statusChip(status) {
  if (status === 'pending') {
    return (
      <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">
        Pending
      </span>
    )
  }
  if (status === 'sent') {
    return (
      <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-400">
        Sent
      </span>
    )
  }
  if (status === 'delivered') {
    return (
      <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-400">
        Delivered
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
        Failed
      </span>
    )
  }
  return (
    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary">
      {status}
    </span>
  )
}

export default function Reminders() {
  const [reminders, setReminders] = useState([])
  const [loading, setLoading] = useState(true)
  const [newReminder, setNewReminder] = useState({
    pet_id: '',
    title: '',
    description: '',
    kind: 'medication',
    target_date: '',
    delivery_method: 'app',
    status: 'pending',
  })
  const toast = useToast()

  const fetchReminders = async () => {
    const res = await fetch(`${API_BASE}/api/petcare/reminders`)
    const data = await res.json()
    setReminders(data)
    setLoading(false)
  }

  useEffect(() => {
    fetchReminders()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    const res = await fetch(`${API_BASE}/api/petcare/reminders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...newReminder,
        pet_id: newReminder.pet_id || null,
        target_date: newReminder.target_date || null,
      }),
    })
    if (res.ok) {
      setNewReminder({
        pet_id: '',
        title: '',
        description: '',
        kind: 'medication',
        target_date: '',
        delivery_method: 'app',
        status: 'pending',
      })
      await fetchReminders()
      toast.success('Created', 'Reminder added')
    } else {
      toast.error('Error', 'Failed to create reminder')
    }
  }

  const handleToggleStatus = async (id, currentStatus) => {
    const newStatus = currentStatus === 'pending' ? 'delivered' : 'pending'
    const res = await fetch(`${API_BASE}/api/petcare/reminders/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    })
    if (res.ok) await fetchReminders()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this reminder?')) return
    const res = await fetch(`${API_BASE}/api/petcare/reminders/${id}`, {
      method: 'DELETE',
    })
    if (res.ok) {
      await fetchReminders()
      toast.success('Deleted', 'Reminder removed')
    }
  }

  if (loading)
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="w-10 h-10 animate-spin text-primary mb-4" />
        <p className="text-text-secondary">Loading reminders...</p>
      </div>
    )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">Reminders</h1>
        <Bell className="w-5 h-5 text-primary" />
      </div>

      <p className="text-text-secondary">
        Stay on top of medications, vaccinations, and care tasks for your pets.
      </p>

      <form onSubmit={handleCreate} className="glass-panel-solid rounded-3xl p-6 space-y-4">
        <h3 className="font-semibold text-text-primary">Add Reminder</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Pet ID
            </label>
            <input
              className={inputClass}
              value={newReminder.pet_id}
              onChange={(e) =>
                setNewReminder({ ...newReminder, pet_id: e.target.value })
              }
              placeholder="e.g. 1"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Title
            </label>
            <input
              className={inputClass}
              value={newReminder.title}
              onChange={(e) =>
                setNewReminder({ ...newReminder, title: e.target.value })
              }
              placeholder="e.g. Heartworm pill"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Description
            </label>
            <input
              className={inputClass}
              value={newReminder.description}
              onChange={(e) =>
                setNewReminder({
                  ...newReminder,
                  description: e.target.value,
                })
              }
              placeholder="e.g. Give monthly heartworm prevention"
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Kind
            </label>
            <select
              className={inputClass}
              value={newReminder.kind}
              onChange={(e) =>
                setNewReminder({ ...newReminder, kind: e.target.value })
              }
            >
              <option value="medication">Medication</option>
              <option value="vaccination">Vaccination</option>
              <option value="care">Care</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Target Date
            </label>
            <input
              className={inputClass}
              type="date"
              value={newReminder.target_date}
              onChange={(e) =>
                setNewReminder({ ...newReminder, target_date: e.target.value })
              }
            />
          </div>
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Delivery Method
            </label>
            <select
              className={inputClass}
              value={newReminder.delivery_method}
              onChange={(e) =>
                setNewReminder({
                  ...newReminder,
                  delivery_method: e.target.value,
                })
              }
            >
              <option value="app">App</option>
              <option value="sms">SMS</option>
              <option value="email">Email</option>
              <option value="push">Push</option>
            </select>
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              className="w-full bg-primary hover:bg-primary/90 text-white px-6 py-2 rounded-lg font-medium transition-colors"
            >
              Add Reminder
            </button>
          </div>
        </div>
      </form>

      <div className="glass-panel-solid rounded-3xl p-6">
        <h3 className="font-semibold text-text-primary mb-4">
          Your Reminders
        </h3>
        {reminders.length === 0 ? (
          <div className="text-center py-8 text-text-muted">
            <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No reminders yet. Add one above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {reminders.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">
                      {r.title}
                    </span>
                    <span className="text-xs text-text-muted">
                      Pet #{r.pet_id || '—'}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-text-secondary mt-1">
                    <span>{r.kind}</span>
                    <span>•</span>
                    <span>{r.delivery_method}</span>
                    <span>•</span>
                    <span>{r.target_date || '—'}</span>
                  </div>
                  {r.description && (
                    <p className="text-xs text-text-muted mt-1">
                      {r.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {statusChip(r.status)}
                  <button
                    onClick={() => handleToggleStatus(r.id, r.status)}
                    className="p-2 rounded hover:bg-white/10 text-text-secondary hover:text-primary transition-colors"
                  >
                    {r.status === 'pending' ? 'Mark Delivered' : 'Reopen'}
                  </button>
                  <button
                    onClick={() => handleDelete(r.id)}
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
