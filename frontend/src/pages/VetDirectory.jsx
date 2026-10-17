import { useEffect, useState } from 'react'
import { AlertTriangle, Loader2, Phone, Plus, Stethoscope, Trash2, X } from 'lucide-react'
import { API_BASE } from '../App'
import { useToast } from '../components/Toast'

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-text-secondary focus:border-primary focus:outline-none'

const emptyForm = {
  name: '',
  phone: '',
  address: '',
  specialty: '',
  hours: '',
  emergency: false,
}

export default function VetDirectory() {
  const toast = useToast()
  const [vets, setVets] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const res = await fetch(`${API_BASE}/api/petcare/vets`)
        if (!res.ok) throw new Error('Failed to load vets')
        const data = await res.json()
        if (!cancelled) setVets(data)
      } catch (err) {
        if (!cancelled) toast.error('Could not load vets', err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [toast])

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) {
      toast.warning('Name required', 'Enter the vet or clinic name.')
      return
    }
    setSaving(true)
    try {
      const res = await fetch(`${API_BASE}/api/petcare/vets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name.trim(),
          phone: form.phone.trim() || null,
          address: form.address.trim() || null,
          specialty: form.specialty.trim() || null,
          hours: form.hours.trim() || null,
          emergency: form.emergency,
        }),
      })
      if (!res.ok) throw new Error('Failed to add vet')
      const created = await res.json()
      setVets((prev) => sortVets([...prev, created]))
      setForm(emptyForm)
      setShowForm(false)
      toast.success('Vet added', `${created.name} was added to your directory.`)
    } catch (err) {
      toast.error('Could not add vet', err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (vet) => {
    if (!window.confirm(`Remove ${vet.name} from your vet directory?`)) return
    try {
      const res = await fetch(`${API_BASE}/api/petcare/vets/${vet.id}`, { method: 'DELETE' })
      if (res.status === 404) {
        toast.error('Not found', 'Vet contact not found.')
        setVets((prev) => prev.filter((v) => v.id !== vet.id))
        return
      }
      if (!res.ok) throw new Error('Failed to delete vet')
      setVets((prev) => prev.filter((v) => v.id !== vet.id))
      toast.success('Removed', `${vet.name} was removed.`)
    } catch (err) {
      toast.error('Could not remove vet', err.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel-solid rounded-xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="font-display text-3xl font-bold gradient-text">Vet Directory</h1>
            <p className="mt-1 text-sm text-text-secondary">
              Keep your veterinarians and clinics in one place.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? 'Cancel' : 'Add vet'}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="grid gap-4 rounded-lg bg-black/20 p-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm text-muted">Name</label>
            <input
              className={inputClass}
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="Dr. Smith / Happy Paws Clinic"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Phone</label>
            <input
              className={inputClass}
              value={form.phone}
              onChange={(e) => update('phone', e.target.value)}
              placeholder="+1 555 0100"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Specialty</label>
            <input
              className={inputClass}
              value={form.specialty}
              onChange={(e) => update('specialty', e.target.value)}
              placeholder="General practice"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted">Hours</label>
            <input
              className={inputClass}
              value={form.hours}
              onChange={(e) => update('hours', e.target.value)}
              placeholder="Mon–Fri 9am–6pm"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm text-muted">Address</label>
            <input
              className={inputClass}
              value={form.address}
              onChange={(e) => update('address', e.target.value)}
              placeholder="123 Main St, Springfield"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-muted sm:col-span-2">
            <input
              type="checkbox"
              checked={form.emergency}
              onChange={(e) => update('emergency', e.target.checked)}
              className="h-4 w-4"
            />
            Emergency / 24-hour vet
          </label>
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Save vet
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center gap-2 rounded-lg bg-black/20 p-6 text-text-secondary">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading vets...
        </div>
      ) : vets.length === 0 ? (
        <div className="glass-panel rounded-xl p-6">
          <div className="flex h-40 flex-col items-center justify-center gap-3 text-center">
            <Stethoscope className="h-10 w-10 text-primary" />
            <h2 className="text-2xl font-bold gradient-text">No vets yet</h2>
            <p className="text-sm text-text-secondary">
              Add your first veterinarian to build your directory.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {vets.map((vet) => (
            <div key={vet.id} className="rounded-lg bg-black/20 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-white">{vet.name}</h3>
                    {vet.emergency && (
                      <span className="flex items-center gap-1 rounded-full bg-red-500/10 px-2 py-0.5 text-xs text-red-400">
                        <AlertTriangle className="h-3 w-3" />
                        Emergency
                      </span>
                    )}
                  </div>
                  <div className="mt-1 space-y-0.5 text-sm text-text-secondary">
                    {vet.specialty && <p>{vet.specialty}</p>}
                    {vet.phone && (
                      <p className="flex items-center gap-1">
                        <Phone className="h-3 w-3" />
                        {vet.phone}
                      </p>
                    )}
                    {vet.hours && <p>{vet.hours}</p>}
                    {vet.address && <p>{vet.address}</p>}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(vet)}
                  className="flex items-center gap-1 rounded-lg bg-white/5 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10"
                >
                  <Trash2 className="h-4 w-4" />
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function sortVets(list) {
  return [...list].sort((a, b) => {
    const em = Number(b.emergency) - Number(a.emergency)
    if (em !== 0) return em
    return String(a.name || '').localeCompare(String(b.name || ''))
  })
}
