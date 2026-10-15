import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CalendarClock,
  HeartPulse,
  ListChecks,
  Loader2,
  MapPin,
  PawPrint,
  Phone,
  Syringe,
} from 'lucide-react'
import { useToast } from '../components/Toast'

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-white/10 p-2.5">
          <Icon className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm text-muted">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  )
}

function formatDueDate(due) {
  return new Date(due).toLocaleDateString()
}

export default function Dashboard() {
  const toast = useToast()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch('/api/petcare/dashboard')
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`)
        const body = await res.json()
        if (!cancelled) setData(body)
      } catch (err) {
        if (!cancelled) {
          setError(err.message)
          toast.error('Dashboard load failed', err.message)
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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="mt-4 text-text-secondary">Loading dashboard…</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="glass-panel rounded-xl p-8 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-red-400" />
        <h2 className="mt-4 text-xl font-bold text-white">Dashboard unavailable</h2>
        <p className="mt-2 text-text-secondary">{error || 'No response from the pet care backend.'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="glass-panel-solid rounded-xl p-6">
        <h1 className="font-display text-3xl font-bold gradient-text">Dashboard</h1>
        <p className="mt-2 text-text-secondary">
          Everything your pets need at a glance.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={PawPrint} label="Pets" value={data.total_pets} />
        <StatCard icon={Syringe} label="Vaccinations due" value={data.due_vaccinations.length} />
        <StatCard icon={CalendarClock} label="Care tasks due" value={data.due_care_tasks.length} />
        <StatCard icon={HeartPulse} label="Emergency vets" value={data.emergency_vets.length} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2">
            <PawPrint className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-white">Pets</h2>
          </div>
          <ul className="mt-4 divide-y divide-white/5">
            {data.pets.map((pet) => (
              <li key={pet.id} className="flex items-center gap-3 py-3">
                <span className="text-2xl">{pet.avatar_emoji || '🐾'}</span>
                <div className="min-w-0">
                  <p className="truncate font-medium text-white">{pet.name}</p>
                  <p className="text-sm text-text-secondary">
                    {pet.species || 'dog'} · {pet.breed || 'Mixed'}
                  </p>
                </div>
                <span className="ml-auto text-sm text-muted">
                  {pet.age_years != null ? `${pet.age_years} yrs` : '—'}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2">
            <Syringe className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-white">Vaccinations due</h2>
          </div>
          {data.due_vaccinations.length === 0 ? (
            <p className="mt-4 text-sm text-muted">No vaccinations due right now.</p>
          ) : (
            <ul className="mt-4 divide-y divide-white/5">
              {data.due_vaccinations.map((v, i) => (
                <li key={i} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-white">{v.name}</p>
                    <p className="text-sm text-text-secondary">Due {formatDueDate(v.due)}</p>
                  </div>
                  {v.status === 'overdue' ? (
                    <span className="rounded-full bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400">
                      {v.days_overdue} d overdue
                    </span>
                  ) : (
                    <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400">
                      {v.days_left} d left
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2">
            <ListChecks className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-white">Care tasks due</h2>
          </div>
          {data.due_care_tasks.length === 0 ? (
            <p className="mt-4 text-sm text-muted">No care tasks due right now.</p>
          ) : (
            <ul className="mt-4 divide-y divide-white/5">
              {data.due_care_tasks.map((t) => (
                <li key={t.pet_id} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-white">{t.pet}</p>
                    <p className="text-sm text-text-secondary">{t.task}</p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      t.status === 'overdue'
                        ? 'bg-red-500/10 text-red-400'
                        : 'bg-amber-500/10 text-amber-400'
                    }`}
                  >
                    {t.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="glass-panel rounded-xl p-5">
          <div className="flex items-center gap-2">
            <HeartPulse className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-white">Emergency vets</h2>
          </div>
          {data.emergency_vets.length === 0 ? (
            <p className="mt-4 text-sm text-muted">No emergency vets saved yet.</p>
          ) : (
            <ul className="mt-4 divide-y divide-white/5">
              {data.emergency_vets.map((vet) => (
                <li key={vet.id} className="py-3">
                  <p className="font-medium text-white">{vet.name}</p>
                  {vet.specialty ? (
                    <p className="text-sm text-text-secondary">{vet.specialty}</p>
                  ) : null}
                  <div className="mt-2 space-y-1 text-sm text-muted">
                    {vet.phone ? (
                      <p className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5" />
                        {vet.phone}
                      </p>
                    ) : null}
                    {vet.address ? (
                      <p className="flex items-start gap-2">
                        <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        {vet.address}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}