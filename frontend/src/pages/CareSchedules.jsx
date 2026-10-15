import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  X,
} from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

const CATEGORIES = [
  { value: 'feeding', label: 'Feeding' },
  { value: 'exercise', label: 'Exercise' },
  { value: 'grooming', label: 'Grooming' },
  { value: 'medication', label: 'Medication' },
  { value: 'hygiene', label: 'Hygiene' },
]

const FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Bi-weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'quarterly', label: 'Quarterly' },
  { value: 'yearly', label: 'Yearly' },
]

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

function formatDueDate(due) {
  if (!due) return '—'
  return new Date(due).toLocaleDateString()
}

export default function CareSchedules() {
  const toast = useToast()
  const [pets, setPets] = useState([])
  const [selectedPetId, setSelectedPetId] = useState('')
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    task: '',
    category: 'care',
    frequency: 'daily',
    time_of_day: '',
    next_due_on: '',
    active: true,
  })
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  // Load pets
  useEffect(() => {
    let cancelled = false
    async function loadPets() {
      try {
        const res = await fetch(`${API_BASE}/api/petcare/pets`)
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setPets(data)
          if (data.length > 0 && !selectedPetId) setSelectedPetId(String(data[0].id))
        }
      } catch (err) {
        if (!cancelled) setLoadError(err.message)
      }
    }
    loadPets()
    return () => { cancelled = true }
  }, [])

  // Load schedules for selected pet
  useEffect(() => {
    if (!selectedPetId) return
    let cancelled = false
    async function loadSchedules() {
      setLoading(true)
      try {
        const res = await fetch(
          `${API_BASE}/api/petcare/pets/${selectedPetId}/care-schedules`
        )
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (!cancelled) setSchedules(data)
      } catch (err) {
        if (!cancelled) setLoadError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadSchedules()
    return () => { cancelled = true }
  }, [selectedPetId])

  const petName = (id) => {
    const pet = pets.find((p) => String(p.id) === String(id))
    return pet ? pet.name : 'Pet'
  }

  const resetForm = () => {
    setForm({
      task: '',
      category: 'care',
      frequency: 'daily',
      time_of_day: '',
      next_due_on: '',
      active: true,
    })
    setEditingId(null)
    setShowForm(false)
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!form.task.trim()) return
    if (!selectedPetId) return
    setSaving(true)
    try {
      const url = editingId
        ? `${API_BASE}/api/petcare/care-schedules/${editingId}`
        : `${API_BASE}/api/petcare/pets/${selectedPetId}/care-schedules`
      const method = editingId ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: form.task.trim(),
          category: form.category,
          frequency: form.frequency,
          time_of_day: form.time_of_day || null,
          next_due_on: form.next_due_on || null,
          active: form.active,
        }),
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      toast.success(
        editingId ? 'Schedule updated' : 'Care schedule added',
        `${form.task} was saved.`
      )
      resetForm()
      // Reload schedules for the pet
      const res2 = await fetch(
        `${API_BASE}/api/petcare/pets/${selectedPetId}/care-schedules`
      )
      if (res2.ok) setSchedules(await res2.json())
    } catch (err) {
      toast.error('Failed to save schedule', err.message)
    } finally {
      setSaving(false)
    }
  }

  const completeSchedule = async (schedule) => {
    setDeletingId(schedule.id)
    try {
      const res = await fetch(
        `${API_BASE}/api/petcare/care-schedules/${schedule.id}/complete`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      toast.success('Task completed', `${schedule.task} rolled forward.`)
      const res2 = await fetch(
        `${API_BASE}/api/petcare/pets/${selectedPetId}/care-schedules`
      )
      if (res2.ok) setSchedules(await res2.json())
    } catch (err) {
      toast.error('Failed to complete task', err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const removeSchedule = async (schedule) => {
    if (!window.confirm(`Remove "${schedule.task}"?`)) return
    setDeletingId(schedule.id)
    try {
      const res = await fetch(
        `${API_BASE}/api/petcare/care-schedules/${schedule.id}`,
        { method: 'DELETE' }
      )
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      toast.success('Schedule removed', `${schedule.task} deleted.`)
      setSchedules(schedules.filter((s) => s.id !== schedule.id))
    } catch (err) {
      toast.error('Failed to remove schedule', err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const startEdit = (schedule) => {
    setForm({
      task: schedule.task,
      category: schedule.category,
      frequency: schedule.frequency,
      time_of_day: schedule.time_of_day || '',
      next_due_on: schedule.next_due_on || '',
      active: schedule.active,
    })
    setEditingId(schedule.id)
    setShowForm(true)
  }

  if (loadError) {
    return (
      <div>
        <header className="glass-panel-solid rounded-xl p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-8 w-8 text-red-400" />
            <h1 className="font-display text-3xl font-bold gradient-text">Care Schedules</h1>
          </div>
          <p className="mt-2 text-text-secondary">
            Feeding, grooming, medication, and care reminders for your pets.
          </p>
        </header>
        <div className="glass-panel mt-6 rounded-xl p-8 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-400" />
          <h2 className="mt-4 text-xl font-bold text-white">Unable to load schedules</h2>
          <p className="mt-2 text-text-secondary">{loadError}</p>
        </div>
      </div>
    )
  }

  if (!pets.length && !loading) {
    return (
      <div>
        <header className="glass-panel-solid rounded-xl p-6">
          <div className="flex items-center gap-3">
            <CalendarClock className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl font-bold gradient-text">Care Schedules</h1>
          </div>
          <p className="mt-2 text-text-secondary">
            Feeding, grooming, medication, and care reminders for your pets.
          </p>
        </header>
        <div className="glass-panel mt-6 rounded-xl p-8 text-center">
          <CalendarClock className="mx-auto h-10 w-10 text-primary" />
          <h2 className="mt-4 text-xl font-bold gradient-text">No pets yet</h2>
          <p className="mt-2 text-sm text-text-secondary">
            Add a pet on the Pets page to start scheduling care.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="glass-panel-solid rounded-xl p-6">
        <div className="flex items-center gap-3">
          <CalendarClock className="h-8 w-8 text-primary" />
          <div>
            <h1 className="font-display text-3xl font-bold gradient-text">Care Schedules</h1>
          </div>
        </div>
        <p className="mt-2 text-text-secondary">
          Feeding, grooming, medication, and care reminders for your pets.
        </p>
        <div className="mt-4">
          <label className="mb-1 block text-sm text-muted" htmlFor="care-pet">
            Pet
          </label>
          <select
            id="care-pet"
            className={inputClass}
            value={selectedPetId}
            onChange={(e) => setSelectedPetId(e.target.value)}
          >
            {pets.map((pet) => (
              <option key={pet.id} value={pet.id} className="bg-neutral-900">
                {pet.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-text-secondary">Loading schedules...</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Care schedule cards */}
          {schedules.length === 0 ? (
            <div className="lg:col-span-3 glass-panel rounded-xl p-8 text-center">
              <CalendarClock className="mx-auto h-10 w-10 text-primary" />
              <h2 className="mt-4 text-xl font-bold gradient-text">No care schedules yet</h2>
              <p className="mt-2 text-sm text-text-secondary">
                Add your first care schedule for {petName(selectedPetId)}.
              </p>
              <button
                onClick={() => setShowForm(true)}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
              >
                <Plus className="h-4 w-4" />
                Add Schedule
              </button>
            </div>
          ) : (
            schedules.map((schedule) => (
              <article
                key={schedule.id}
                className="glass-panel rounded-xl p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate font-semibold text-white">{schedule.task}</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary uppercase">
                        {schedule.category}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-text-secondary">
                      {schedule.frequency.charAt(0).toUpperCase() + schedule.frequency.slice(1)}
                      {schedule.time_of_day ? ` · ${schedule.time_of_day}` : ''}
                    </p>
                    <p className="mt-1 text-xs text-text-secondary">
                      Next due: {formatDueDate(schedule.next_due_on)}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span>{statusChip(schedule.status)}</span>
                    <button
                      onClick={() => startEdit(schedule)}
                      className="rounded-lg p-2 text-muted transition hover:bg-white/10 hover:text-white"
                      aria-label={`Edit ${schedule.task}`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => completeSchedule(schedule)}
                      disabled={deletingId === schedule.id}
                      className="rounded-lg p-2 text-green-400 transition hover:bg-green-500/10 disabled:opacity-50"
                      aria-label={`Complete ${schedule.task}`}
                    >
                      {deletingId === schedule.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4" />
                      )}
                    </button>
                    <button
                      onClick={() => removeSchedule(schedule)}
                      disabled={deletingId === schedule.id}
                      className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                      aria-label={`Remove ${schedule.task}`}
                    >
                      {deletingId === schedule.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>
              </article>
            ))
          )}

          {/* Add / Edit form */}
          {showForm && (
            <div className="lg:col-span-3 glass-panel rounded-xl p-5">
              <form onSubmit={submit} className="grid gap-4 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-sm text-muted">Task</label>
                  <input
                    className={inputClass}
                    value={form.task}
                    onChange={(e) => setForm({ ...form, task: e.target.value })}
                    placeholder="e.g. Evening walk"
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted">Category</label>
                  <select
                    className={inputClass}
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c.value} value={c.value} className="bg-neutral-900">
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted">Frequency</label>
                  <select
                    className={inputClass}
                    value={form.frequency}
                    onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                  >
                    {FREQUENCIES.map((f) => (
                      <option key={f.value} value={f.value} className="bg-neutral-900">
                        {f.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted">Time of day</label>
                  <input
                    type="time"
                    className={inputClass}
                    value={form.time_of_day}
                    onChange={(e) => setForm({ ...form, time_of_day: e.target.value })}
                    placeholder="e.g. 18:00"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted">Next due date</label>
                  <input
                    type="date"
                    className={inputClass}
                    value={form.next_due_on}
                    onChange={(e) => setForm({ ...form, next_due_on: e.target.value })}
                  />
                </div>
                <div className="sm:col-span-2 flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-muted cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={form.active}
                      onChange={(e) => setForm({ ...form, active: e.target.checked })}
                      className="h-4 w-4"
                    />
                    Active
                  </label>
                </div>
                <div className="sm:col-span-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={resetForm}
                    className="rounded-lg border border-white/10 px-4 py-2 text-sm text-text-secondary transition hover:bg-white/5"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving || !form.task.trim()}
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                    {editingId ? 'Save Changes' : 'Add Schedule'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
