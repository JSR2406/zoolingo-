import { useEffect, useState } from 'react'
import {
  Activity,
  Loader2,
  Plus,
  Scale,
  Stethoscope,
  Syringe,
  Trash2,
  X,
} from 'lucide-react'
import { useToast } from '../components/Toast'
import { API_BASE } from '../App'

const RECORD_TYPES = ['note', 'medication', 'symptom', 'appointment', 'other']

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

function formatDate(value) {
  if (!value) return 'Unknown'
  const d = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString()
}

function sortVax(list) {
  return [...list].sort((a, b) => {
    if (!a.next_due_on && b.next_due_on) return -1
    if (a.next_due_on && !b.next_due_on) return 1
    return String(a.next_due_on).localeCompare(String(b.next_due_on))
  })
}

function sortByDateDesc(list, field) {
  return [...list].sort((a, b) =>
    String(b[field] || '').localeCompare(String(a[field] || ''))
  )
}

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
  return (
    <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary">
      Up to date
    </span>
  )
}

export default function Health() {
  const { success, error } = useToast()

  const [pets, setPets] = useState([])
  const [selectedPetId, setSelectedPetId] = useState('')

  const [vaccinations, setVaccinations] = useState([])
  const [weights, setWeights] = useState([])
  const [records, setRecords] = useState([])

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [showVaxForm, setShowVaxForm] = useState(false)
  const [vaxForm, setVaxForm] = useState({
    name: '',
    administered_on: '',
    next_due_on: '',
    administered_at: '',
    notes: '',
  })
  const [savingVax, setSavingVax] = useState(false)

  const [showWeightForm, setShowWeightForm] = useState(false)
  const [weightForm, setWeightForm] = useState({ weight_kg: '', logged_on: '' })
  const [savingWeight, setSavingWeight] = useState(false)

  const [showRecordForm, setShowRecordForm] = useState(false)
  const [recordForm, setRecordForm] = useState({
    record_type: 'note',
    title: '',
    description: '',
    recorded_on: '',
  })
  const [savingRecord, setSavingRecord] = useState(false)

  const [deletingVaxId, setDeletingVaxId] = useState(null)
  const [deletingRecordId, setDeletingRecordId] = useState(null)

  const petName = (id) => {
    const pet = pets.find((p) => String(p.id) === String(id))
    return pet ? pet.name : 'Pet'
  }

  useEffect(() => {
    let cancelled = false
    async function loadPets() {
      try {
        const res = await fetch(`${API_BASE}/api/petcare/pets`)
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        setPets(data)
        if (data.length > 0) setSelectedPetId(String(data[0].id))
      } catch (err) {
        if (!cancelled) setLoadError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadPets()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!selectedPetId) return
    let cancelled = false
    async function loadHealth() {
      setLoading(true)
      try {
        const base = `${API_BASE}/api/petcare/pets/${selectedPetId}`
        const [vaxRes, weightRes, recordRes] = await Promise.all([
          fetch(`${base}/vaccinations`),
          fetch(`${base}/weights`),
          fetch(`${base}/health-records`),
        ])
        if (!vaxRes.ok) throw new Error(`Request failed with status ${vaxRes.status}`)
        if (!weightRes.ok) throw new Error(`Request failed with status ${weightRes.status}`)
        if (!recordRes.ok) throw new Error(`Request failed with status ${recordRes.status}`)
        const vaxData = await vaxRes.json()
        const weightData = await weightRes.json()
        const recordData = await recordRes.json()
        if (cancelled) return
        setVaccinations(vaxData)
        setWeights(weightData)
        setRecords(recordData)
        setLoadError('')
      } catch (err) {
        if (!cancelled) setLoadError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadHealth()
    return () => {
      cancelled = true
    }
  }, [selectedPetId])

  async function addVaccination() {
    if (!selectedPetId || !vaxForm.name.trim()) return
    setSavingVax(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/petcare/pets/${selectedPetId}/vaccinations`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: vaxForm.name.trim(),
            administered_on: vaxForm.administered_on || null,
            next_due_on: vaxForm.next_due_on || null,
            administered_at: vaxForm.administered_at,
            notes: vaxForm.notes,
          }),
        }
      )
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      const created = await res.json()
      setVaccinations(sortVax([...vaccinations, created]))
      setVaxForm({
        name: '',
        administered_on: '',
        next_due_on: '',
        administered_at: '',
        notes: '',
      })
      setShowVaxForm(false)
      success('Vaccination added', `${created.name} recorded for ${petName(selectedPetId)}`)
    } catch (err) {
      error('Could not add vaccination', err.message)
    } finally {
      setSavingVax(false)
    }
  }

  async function addWeight() {
    const kg = Number(weightForm.weight_kg)
    if (!selectedPetId || !Number.isFinite(kg) || kg <= 0) return
    setSavingWeight(true)
    try {
      const res = await fetch(`${API_BASE}/api/petcare/pets/${selectedPetId}/weights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          weight_kg: kg,
          logged_on: weightForm.logged_on || null,
        }),
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      const created = await res.json()
      setWeights(sortByDateDesc([...weights, created], 'logged_on'))
      setWeightForm({ weight_kg: '', logged_on: '' })
      setShowWeightForm(false)
      success('Weight logged', `${kg} kg recorded for ${petName(selectedPetId)}`)
    } catch (err) {
      error('Could not log weight', err.message)
    } finally {
      setSavingWeight(false)
    }
  }

  async function addRecord() {
    if (!selectedPetId || !recordForm.title.trim()) return
    setSavingRecord(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/petcare/pets/${selectedPetId}/health-records`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            record_type: recordForm.record_type,
            title: recordForm.title.trim(),
            description: recordForm.description,
            recorded_on: recordForm.recorded_on || null,
          }),
        }
      )
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      const created = await res.json()
      setRecords(sortByDateDesc([...records, created], 'recorded_on'))
      setRecordForm({ record_type: 'note', title: '', description: '', recorded_on: '' })
      setShowRecordForm(false)
      success('Health record added', `${created.title} added for ${petName(selectedPetId)}`)
    } catch (err) {
      error('Could not add health record', err.message)
    } finally {
      setSavingRecord(false)
    }
  }

  async function deleteVaccination(vax) {
    if (!window.confirm(`Remove ${vax.name}?`)) return
    setDeletingVaxId(vax.id)
    try {
      const res = await fetch(`${API_BASE}/api/petcare/vaccinations/${vax.id}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      setVaccinations(vaccinations.filter((v) => v.id !== vax.id))
      success('Vaccination removed', `${vax.name} deleted`)
    } catch (err) {
      error('Could not remove vaccination', err.message)
    } finally {
      setDeletingVaxId(null)
    }
  }

  async function deleteRecord(rec) {
    if (!window.confirm(`Remove ${rec.title}?`)) return
    setDeletingRecordId(rec.id)
    try {
      const res = await fetch(`${API_BASE}/api/petcare/health-records/${rec.id}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      setRecords(records.filter((r) => r.id !== rec.id))
      success('Health record removed', `${rec.title} deleted`)
    } catch (err) {
      error('Could not remove health record', err.message)
    } finally {
      setDeletingRecordId(null)
    }
  }

  if (loadError) {
    return (
      <div>
        <header className="glass-panel-solid rounded-xl p-6">
          <div className="flex items-center gap-3">
            <Activity className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl font-bold gradient-text">Health</h1>
          </div>
          <p className="mt-2 text-text-secondary">
            Track vaccinations, weight, and health records for your pets.
          </p>
        </header>
        <div className="glass-panel mt-6 rounded-xl p-8 text-center">
          <Activity className="mx-auto h-8 w-8 text-red-400" />
          <h2 className="mt-4 text-xl font-bold text-white">Health data could not load</h2>
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
            <Activity className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl font-bold gradient-text">Health</h1>
          </div>
          <p className="mt-2 text-text-secondary">
            Track vaccinations, weight, and health records for your pets.
          </p>
        </header>
        <div className="glass-panel mt-6 rounded-xl p-8 text-center">
          <Activity className="mx-auto h-10 w-10 text-primary" />
          <h2 className="mt-4 text-xl font-bold gradient-text">No pets yet</h2>
          <p className="mt-2 text-sm text-text-secondary">
            Add a pet on the Pets page to start tracking their health.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="glass-panel-solid rounded-xl p-6">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-primary" />
          <div>
            <h1 className="font-display text-3xl font-bold gradient-text">Health</h1>
          </div>
        </div>
        <p className="mt-2 text-text-secondary">
          Track vaccinations, weight, and health records for your pets.
        </p>
        <div className="mt-4">
          <label className="mb-1 block text-sm text-muted" htmlFor="health-pet">
            Pet
          </label>
          <select
            id="health-pet"
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
          <p className="mt-4 text-text-secondary">Loading health data...</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="glass-panel rounded-xl p-5 lg:col-span-2">
            <div className="flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                <Syringe className="h-5 w-5 text-primary" />
                Vaccinations
              </h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                onClick={() => setShowVaxForm((v) => !v)}
              >
                {showVaxForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                {showVaxForm ? 'Cancel' : 'Add Vaccination'}
              </button>
            </div>

            {showVaxForm && (
              <div className="mt-4 grid gap-4 rounded-lg bg-black/20 p-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="vax-name">
                    Vaccine name
                  </label>
                  <input
                    id="vax-name"
                    className={inputClass}
                    value={vaxForm.name}
                    onChange={(e) => setVaxForm({ ...vaxForm, name: e.target.value })}
                    placeholder="Rabies, DHPP, ..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="vax-administered-at">
                    Administered at
                  </label>
                  <input
                    id="vax-administered-at"
                    className={inputClass}
                    value={vaxForm.administered_at}
                    onChange={(e) => setVaxForm({ ...vaxForm, administered_at: e.target.value })}
                    placeholder="e.g. Happy Paws Clinic"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="vax-administered-on">
                    Administered on
                  </label>
                  <input
                    id="vax-administered-on"
                    type="date"
                    className={inputClass}
                    value={vaxForm.administered_on}
                    onChange={(e) => setVaxForm({ ...vaxForm, administered_on: e.target.value })}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="vax-next-due">
                    Next due
                  </label>
                  <input
                    id="vax-next-due"
                    type="date"
                    className={inputClass}
                    value={vaxForm.next_due_on}
                    onChange={(e) => setVaxForm({ ...vaxForm, next_due_on: e.target.value })}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-sm text-muted" htmlFor="vax-notes">
                    Notes
                  </label>
                  <textarea
                    id="vax-notes"
                    className={`${inputClass} min-h-20 resize-y`}
                    value={vaxForm.notes}
                    onChange={(e) => setVaxForm({ ...vaxForm, notes: e.target.value })}
                    placeholder="Optional notes"
                  />
                </div>
                <div className="sm:col-span-2 flex justify-end">
                  <button
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={addVaccination}
                    disabled={savingVax || !vaxForm.name.trim()}
                  >
                    {savingVax && <Loader2 className="h-4 w-4 animate-spin" />}
                    Save Vaccination
                  </button>
                </div>
              </div>
            )}

            {vaccinations.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {sortVax(vaccinations).map((vax) => (
                  <li
                    key={vax.id}
                    className="flex items-center justify-between gap-3 rounded-lg bg-black/20 p-3"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-white">{vax.name}</p>
                        {statusChip(vax.status)}
                      </div>
                      <p className="mt-0.5 text-xs text-text-secondary">
                        Administered {formatDate(vax.administered_on)}
                        {vax.next_due_on ? ` · Next due ${formatDate(vax.next_due_on)}` : ''}
                        {vax.administered_at ? ` · ${vax.administered_at}` : ''}
                      </p>
                      {vax.notes ? <p className="mt-1 text-sm text-muted">{vax.notes}</p> : null}
                    </div>
                    <button
                      className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                      onClick={() => deleteVaccination(vax)}
                      disabled={deletingVaxId === vax.id}
                      aria-label={`Remove ${vax.name}`}
                    >
                      {deletingVaxId === vax.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-text-secondary">No vaccinations recorded yet.</p>
            )}
          </section>

          <section className="glass-panel rounded-xl p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                <Scale className="h-5 w-5 text-primary" />
                Weight Log
              </h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                onClick={() => setShowWeightForm((v) => !v)}
              >
                {showWeightForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                {showWeightForm ? 'Cancel' : 'Log Weight'}
              </button>
            </div>

            {showWeightForm && (
              <div className="mt-4 grid gap-4 rounded-lg bg-black/20 p-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="weight-kg">
                    Weight (kg)
                  </label>
                  <input
                    id="weight-kg"
                    type="number"
                    step="0.1"
                    min="0"
                    className={inputClass}
                    value={weightForm.weight_kg}
                    onChange={(e) => setWeightForm({ ...weightForm, weight_kg: e.target.value })}
                    placeholder="e.g. 12.5"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="weight-logged-on">
                    Date
                  </label>
                  <input
                    id="weight-logged-on"
                    type="date"
                    className={inputClass}
                    value={weightForm.logged_on}
                    onChange={(e) => setWeightForm({ ...weightForm, logged_on: e.target.value })}
                  />
                </div>
                <div className="sm:col-span-2 flex justify-end">
                  <button
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={addWeight}
                    disabled={savingWeight || !Number(weightForm.weight_kg)}
                  >
                    {savingWeight && <Loader2 className="h-4 w-4 animate-spin" />}
                    Save Weight
                  </button>
                </div>
              </div>
            )}

            {weights.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {sortByDateDesc(weights, 'logged_on').map((w) => (
                  <li
                    key={w.id}
                    className="flex items-center justify-between rounded-lg bg-black/20 p-3"
                  >
                    <p className="font-medium text-white">{w.weight_kg} kg</p>
                    <p className="text-xs text-text-secondary">{formatDate(w.logged_on)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-text-secondary">No weights logged yet.</p>
            )}
          </section>

          <section className="glass-panel rounded-xl p-5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                <Stethoscope className="h-5 w-5 text-primary" />
                Health Records
              </h2>
              <button
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                onClick={() => setShowRecordForm((v) => !v)}
              >
                {showRecordForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                {showRecordForm ? 'Cancel' : 'Add Record'}
              </button>
            </div>

            {showRecordForm && (
              <div className="mt-4 grid gap-4 rounded-lg bg-black/20 p-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="record-type">
                    Type
                  </label>
                  <select
                    id="record-type"
                    className={inputClass}
                    value={recordForm.record_type}
                    onChange={(e) => setRecordForm({ ...recordForm, record_type: e.target.value })}
                  >
                    {RECORD_TYPES.map((t) => (
                      <option key={t} value={t} className="bg-neutral-900">
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="record-title">
                    Title
                  </label>
                  <input
                    id="record-title"
                    className={inputClass}
                    value={recordForm.title}
                    onChange={(e) => setRecordForm({ ...recordForm, title: e.target.value })}
                    placeholder="e.g. Vet checkup"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted" htmlFor="record-on">
                    Date
                  </label>
                  <input
                    id="record-on"
                    type="date"
                    className={inputClass}
                    value={recordForm.recorded_on}
                    onChange={(e) => setRecordForm({ ...recordForm, recorded_on: e.target.value })}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="mb-1 block text-sm text-muted" htmlFor="record-desc">
                    Details
                  </label>
                  <textarea
                    id="record-desc"
                    className={`${inputClass} min-h-20 resize-y`}
                    value={recordForm.description}
                    onChange={(e) =>
                      setRecordForm({ ...recordForm, description: e.target.value })
                    }
                    placeholder="Optional details"
                  />
                </div>
                <div className="sm:col-span-2 flex justify-end">
                  <button
                    className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                    onClick={addRecord}
                    disabled={savingRecord || !recordForm.title.trim()}
                  >
                    {savingRecord && <Loader2 className="h-4 w-4 animate-spin" />}
                    Save Record
                  </button>
                </div>
              </div>
            )}

            {records.length > 0 ? (
              <ul className="mt-4 space-y-2">
                {sortByDateDesc(records, 'recorded_on').map((rec) => (
                  <li
                    key={rec.id}
                    className="flex items-center justify-between gap-3 rounded-lg bg-black/20 p-3"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-white">{rec.title}</p>
                        <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-text-secondary">
                          {rec.record_type.charAt(0).toUpperCase() + rec.record_type.slice(1)}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-text-secondary">
                        {formatDate(rec.recorded_on)}
                      </p>
                      {rec.description ? (
                        <p className="mt-1 text-sm text-muted">{rec.description}</p>
                      ) : null}
                    </div>
                    <button
                      className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                      onClick={() => deleteRecord(rec)}
                      disabled={deletingRecordId === rec.id}
                      aria-label={`Remove ${rec.title}`}
                    >
                      {deletingRecordId === rec.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-text-secondary">No health records yet.</p>
            )}
          </section>
        </div>
      )}
    </div>
  )
}