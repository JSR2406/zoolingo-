import { useEffect, useState } from 'react'
import { AlertTriangle, Loader2, Pencil, Plus, PawPrint, Trash2, X } from 'lucide-react'
import { useToast } from '../components/Toast'

const API_BASE = import.meta.env.VITE_API_URL || ''

const SPECIES = ['dog', 'cat', 'bird', 'fish', 'hamster', 'rabbit', 'other']
const GENDERS = ['male', 'female', 'unknown']

const emptyForm = {
  name: '',
  species: 'dog',
  breed: '',
  gender: 'unknown',
  date_of_birth: '',
  weight_kg: 0,
  microchip_id: '',
  avatar_emoji: '🐾',
  notes: '',
}

function Pets() {
  const toast = useToast()
  const [pets, setPets] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reload, setReload] = useState(0)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [form, setForm] = useState(emptyForm)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(`${API_BASE}/api/petcare/pets`)
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const data = await res.json()
        if (!cancelled) setPets(data)
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          toast.error('Failed to load pets', err.message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [reload])

  const updateField = (key, value) => setForm((f) => ({ ...f, [key]: value }))

  const startAdd = () => {
    setForm(emptyForm)
    setEditingId(null)
    setShowForm(true)
  }

  const startEdit = (pet) => {
    setForm({
      name: pet.name,
      species: pet.species,
      breed: pet.breed || '',
      gender: pet.gender,
      date_of_birth: pet.date_of_birth ? pet.date_of_birth.slice(0, 10) : '',
      weight_kg: pet.weight_kg ?? 0,
      microchip_id: pet.microchip_id || '',
      avatar_emoji: pet.avatar_emoji || '🐾',
      notes: pet.notes || '',
    })
    setEditingId(pet.id)
    setShowForm(true)
  }

  const cancelForm = () => {
    setShowForm(false)
    setEditingId(null)
    setForm(emptyForm)
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    setSaving(true)
    const payload = {
      name: form.name.trim(),
      species: form.species,
      breed: form.breed.trim(),
      gender: form.gender,
      date_of_birth: form.date_of_birth || null,
      weight_kg: Number(form.weight_kg) || 0,
      microchip_id: form.microchip_id.trim(),
      avatar_emoji: form.avatar_emoji.trim() || '🐾',
      notes: form.notes.trim(),
    }
    try {
      const url = editingId ? `${API_BASE}/api/petcare/pets/${editingId}` : `${API_BASE}/api/petcare/pets`
      const method = editingId ? 'PUT' : 'POST'
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      toast.success(editingId ? 'Pet updated' : 'Pet added', `${payload.name} was saved to your pet family.`)
      cancelForm()
      setReload((r) => r + 1)
    } catch (err) {
      toast.error('Failed to save pet', err.message)
    } finally {
      setSaving(false)
    }
  }

  const removePet = async (pet) => {
    if (!window.confirm(`Remove ${pet.name} from your pet family? This cannot be undone.`)) return
    setDeletingId(pet.id)
    try {
      const res = await fetch(`${API_BASE}/api/petcare/pets/${pet.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
      toast.success('Pet removed', `${pet.name} was removed from your family.`)
      setReload((r) => r + 1)
    } catch (err) {
      toast.error('Failed to remove pet', err.message)
    } finally {
      setDeletingId(null)
    }
  }

  const inputClass =
    'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

  const renderForm = () => (
    <section className="glass-panel rounded-xl p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">{editingId ? 'Edit Pet' : 'Add a Pet'}</h2>
        <button onClick={cancelForm} className="rounded-lg p-2 text-muted transition hover:bg-white/10 hover:text-white" aria-label="Close form">
          <X className="h-5 w-5" />
        </button>
      </div>
      <form onSubmit={submit} className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm text-muted">Name</label>
          <input
            className={inputClass}
            value={form.name}
            onChange={(e) => updateField('name', e.target.value)}
            placeholder="e.g. Milo"
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Avatar emoji</label>
          <input
            className={inputClass}
            value={form.avatar_emoji}
            onChange={(e) => updateField('avatar_emoji', e.target.value)}
            placeholder="🐾"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Species</label>
          <select
            className={inputClass}
            value={form.species}
            onChange={(e) => updateField('species', e.target.value)}
          >
            {SPECIES.map((s) => (
              <option key={s} value={s} className="bg-neutral-900">
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Breed</label>
          <input
            className={inputClass}
            value={form.breed}
            onChange={(e) => updateField('breed', e.target.value)}
            placeholder="e.g. Golden Retriever"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Gender</label>
          <select
            className={inputClass}
            value={form.gender}
            onChange={(e) => updateField('gender', e.target.value)}
          >
            {GENDERS.map((g) => (
              <option key={g} value={g} className="bg-neutral-900">
                {g}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Date of birth</label>
          <input
            type="date"
            className={inputClass}
            value={form.date_of_birth}
            onChange={(e) => updateField('date_of_birth', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Weight (kg)</label>
          <input
            type="number"
            step="0.1"
            min="0"
            className={inputClass}
            value={form.weight_kg}
            onChange={(e) => updateField('weight_kg', e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted">Microchip ID</label>
          <input
            className={inputClass}
            value={form.microchip_id}
            onChange={(e) => updateField('microchip_id', e.target.value)}
            placeholder="Optional"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-sm text-muted">Notes</label>
          <textarea
            className={`${inputClass} min-h-24 resize-y`}
            value={form.notes}
            onChange={(e) => updateField('notes', e.target.value)}
            placeholder="Allergies, medications, quirks..."
          />
        </div>
        <div className="sm:col-span-2 flex justify-end gap-2">
          <button
            type="button"
            onClick={cancelForm}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-text-secondary transition hover:bg-white/5"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !form.name.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {editingId ? 'Save Changes' : 'Add Pet'}
          </button>
        </div>
      </form>
    </section>
  )

  const renderPets = () => {
    if (pets.length === 0) {
      return (
        <section className="glass-panel rounded-xl p-6">
          <div className="flex flex-col items-center justify-center gap-3 py-10 text-center">
            <PawPrint className="h-10 w-10 text-primary" />
            <h2 className="text-xl font-bold gradient-text">No pets yet</h2>
            <p className="text-sm text-text-secondary">Add your first pet to start tracking care.</p>
          </div>
        </section>
      )
    }
    return (
      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {pets.map((pet) => (
          <article key={pet.id} className="glass-panel rounded-xl p-5">
            <div className="flex items-start gap-3">
              <span className="text-3xl">{pet.avatar_emoji}</span>
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-semibold text-white">{pet.name}</h3>
                <p className="text-sm text-text-secondary">
                  {pet.species}
                  {pet.breed ? ` · ${pet.breed}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 gap-1">
                <button
                  onClick={() => startEdit(pet)}
                  className="rounded-lg p-2 text-muted transition hover:bg-white/10 hover:text-white"
                  aria-label={`Edit ${pet.name}`}
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  onClick={() => removePet(pet)}
                  disabled={deletingId === pet.id}
                  className="rounded-lg p-2 text-muted transition hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50"
                  aria-label={`Remove ${pet.name}`}
                >
                  {deletingId === pet.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted">Age</dt>
                <dd className="text-white">{pet.age_years != null ? `${pet.age_years.toFixed(1)} yrs` : 'Unknown'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Weight</dt>
                <dd className="text-white">{pet.weight_kg != null ? `${pet.weight_kg} kg` : 'Unknown'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Gender</dt>
                <dd className="capitalize text-white">{pet.gender}</dd>
              </div>
              {pet.microchip_id ? (
                <div className="flex justify-between">
                  <dt className="text-muted">Microchip</dt>
                  <dd className="text-white">{pet.microchip_id}</dd>
                </div>
              ) : null}
            </dl>
            {pet.notes ? (
              <p className="mt-3 rounded-lg bg-black/20 p-3 text-sm text-text-secondary">{pet.notes}</p>
            ) : null}
          </article>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="glass-panel-solid rounded-xl p-6">
        <h1 className="font-display text-3xl font-bold gradient-text">Pets</h1>
        <p className="mt-2 text-text-secondary">Keep every member of your pet family up to date.</p>
      </header>

      <div className="flex justify-end">
        <button
          onClick={showForm ? cancelForm : startAdd}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? 'Cancel' : 'Add Pet'}
        </button>
      </div>

      {showForm ? renderForm() : null}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-text-secondary">Loading pets...</p>
        </div>
      ) : error ? (
        <div className="glass-panel rounded-xl p-8 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-400" />
          <h2 className="mt-4 text-xl font-bold text-white">Could not load pets</h2>
          <p className="mt-2 text-text-secondary">{error}</p>
        </div>
      ) : (
        renderPets()
      )}
    </div>
  )
}

export default Pets