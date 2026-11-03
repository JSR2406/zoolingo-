import React, { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  PawPrint,
  HeartPulse,
  CalendarClock,
  ListChecks,
  MapPin,
  Phone,
  Syringe,
  Zap,
  Volume2,
  Sparkles,
  ChevronRight,
  Clock,
  Play,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { useToast } from '../components/Toast';

// --- Reusable Components ---

function StatCard({ icon: Icon, label, value, subtitle, trend }) {
  return (
    <div className="glass-panel rounded-2xl p-6 group relative overflow-hidden">
      {/* Subtle gradient border accent */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-cyan-400 to-purple-500 opacity-60" />
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-white/10 p-2.5">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <span className="ml-auto text-right text-xs text-muted uppercase tracking-wider font-semibold">
            {label}
          </span>
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-white">{value}</span>
        {subtitle && <span className="text-sm text-muted">{subtitle}</span>}
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          {trend.positive ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3 h-3" /> {trend.value}%
            </span>
          ) : (
            <span className="flex items-center gap-1 text-red-400">
              <AlertTriangle className="w-3 h-3" /> {trend.value}%
            </span>
          )}
          <span className="text-muted">vs last week</span>
        </div>
      )}
    </div>
  );
}

function PetCard({ pet, onClick }) {
  const age = pet.age_years != null ? `${Math.floor(pet.age_years)} yrs` : '—';
  return (
    <div
      className="glass-panel rounded-xl p-4 cursor-pointer hover:bg-white/5 transition-colors group border border-transparent hover:border-primary/50"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="text-3xl filter drop-shadow-lg">{pet.avatar_emoji || '🐾'}</div>
        <span className="flex items-center gap-1 text-xs font-medium bg-white/5 px-2 py-1 rounded text-green-400 border border-green-500/20">
          {pet.species === 'dog' ? '🐶' : pet.species === 'cat' ? '🐱' : '🐾'} {pet.species}
        </span>
      </div>
      <h3 className="font-bold text-white text-lg truncate">{pet.name}</h3>
      <p className="text-sm text-muted mt-1">
        {pet.breed || 'Mixed breed'} · {pet.gender || '—'}
      </p>
      <div className="mt-4 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-muted">
          <Clock className="w-3 h-3" /> {age}
        </span>
        <ChevronRight className="w-4 h-4 text-muted/50 group-hover:text-primary transition-colors" />
      </div>
      {pet.weight_kg && (
        <div className="mt-2 flex items-center gap-1 text-xs text-muted">
          <span className="flex items-center gap-0.5">
            <span className="w-1 h-1 rounded-full bg-primary" />
            {pet.weight_kg} kg
          </span>
        </div>
      )}
    </div>
  );
}

function AlertCard({ icon: Icon, title, items, onViewAll }) {
  return (
    <div className="glass-panel rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="rounded-lg bg-red-500/10 p-2">
            <Icon className="h-5 w-5 text-red-400" />
          </div>
          <h2 className="font-bold text-white">{title}</h2>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-xs text-primary hover:text-primary/80 hover:underline transition-colors"
          >
            View all →
          </button>
        )}
      </div>
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="text-center py-6 text-muted">
            <span className="text-2xl mb-2">✨</span>
            <p className="text-sm">All clear!</p>
          </div>
        ) : (
          items.map((item, i) => (
            <div key={i} className="flex items-center justify-between gap-3 py-2">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-white truncate">{item.name || item.title || item.task}</p>
                <p className="text-xs text-muted">
                  {item.due_on ? `Due ${new Date(item.due_on).toLocaleDateString()}` : ''}
                  {item.days_overdue != null ? `· ${item.days_overdue}d overdue` : ''}
                  {item.days_left != null ? `· ${item.days_left}d left` : ''}
                </p>
              </div>
              <span
                className={`px-2 py-1 rounded text-xs font-bold ${
                  item.status === 'overdue'
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : item.status === 'due'
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }`}
              >
                {item.status}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function QuickActionCard({ icon: Icon, label, description, onClick, color = 'primary' }) {
  return (
    <button
      onClick={onClick}
      className="glass-panel rounded-xl p-4 cursor-pointer flex flex-col items-center gap-3 hover:bg-white/5 transition-all border border-transparent hover:border-white/10 group"
    >
      <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-white/5 group-hover:bg-primary/20 group-hover:text-primary transition-all">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="font-semibold text-white text-sm">{label}</h3>
      <p className="text-xs text-muted text-center leading-tight">{description}</p>
    </button>
  );
}

function RecentTranslationItem({ translation, onPlay, onClick }) {
  const isAssisted = translation.translation?.startsWith('[AI]') || translation.translation?.startsWith('🧠');
  const emotionColor = {
    happy: 'text-emerald-400',
    angry: 'text-red-400',
    sad: 'text-blue-400',
    hungry: 'text-orange-400',
    pain: 'text-purple-400',
    excited: 'text-emerald-400',
    scared: 'text-rose-400',
    curious: 'text-cyan-400',
  }[translation.emotion?.toLowerCase()] || 'text-text-secondary';

  return (
    <div
      onClick={onClick}
      className="glass-panel rounded-lg p-3 cursor-pointer hover:bg-white/5 transition-colors group border border-transparent hover:border-white/5"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`font-medium text-white ${emotionColor}`}>{translation.emotion}</span>
            {translation.confidence != null && (
              <span className="text-xs text-muted">{(translation.confidence * 100).toFixed(0)}%</span>
            )}
            {translation.confidence != null && translation.confidence < 0.6 && (
              <span className="flex items-center gap-1 text-amber-400 text-xs">
                <AlertTriangle className="w-3 h-3" /> Low confidence
              </span>
            )}
          </div>
          <p className="font-bold text-white text-sm truncate">{translation.translation}</p>
          <p className="text-xs text-muted mt-0.5">
            {translation.language === 'hi-IN' ? 'हिंदी' : 'English'} · {translation.animal}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPlay(translation);
            }}
            className="p-1.5 rounded bg-white/5 hover:bg-primary/10 text-primary hover:text-white transition-colors"
          >
            <Volume2 className="w-4 h-4" />
          </button>
          <ChevronRight className="w-3 h-3 text-muted/50 group-hover:text-primary transition-colors" />
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[10px] text-muted">
        <span className="flex items-center gap-1">
          <Clock className="w-2.5 h-2.5" />
          {translation.created_at ? new Date(translation.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
        </span>
        {translation.assisted && (
          <span className="flex items-center gap-1 text-cyan-400">
            <Zap className="w-2.5 h-2.5" /> AI-assisted
          </span>
        )}
      </div>
    </div>
  );
}

// --- Main Dashboard Component ---

export default function Dashboard() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'activity'
  const [nowPlaying, setNowPlaying] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch('/api/petcare/dashboard');
        if (!res.ok) throw new Error(`Request failed with status ${res.status}`);
        const body = await res.json();
        if (!cancelled) setData(body);
      } catch (err) {
        if (!cancelled) {
          // Use fallback demo data when backend is unavailable
          setData({
            total_pets: 2,
            pets: [
              { id: 1, name: 'Buddy', species: 'dog', breed: 'Golden Retriever', gender: 'male', date_of_birth: '2021-06-14', weight_kg: 27.5, age_years: 5.4, avatar_emoji: '🐶', notes: '', microchip_id: '' },
              { id: 2, name: 'Mia', species: 'cat', breed: 'Domestic Shorthair', gender: 'female', date_of_birth: '2023-02-01', weight_kg: 4.2, age_years: 3.7, avatar_emoji: '🐱', notes: '', microchip_id: '' },
            ],
            due_vaccinations: [
              { name: 'Rabies', due_on: '2026-01-10', days_overdue: 280, status: 'overdue' },
              { name: 'Bordetella', due_on: '2025-12-17', days_left: 45, status: 'due' },
            ],
            due_care_tasks: [
              { pet: 'Buddy', task: 'Evening walk', status: 'due' },
              { pet: 'Mia', task: 'Litter box clean', status: 'overdue' },
            ],
            emergency_vets: [
              { id: 1, name: 'CityVet Emergency', specialty: 'emergency', phone: '(555) 010-0911', hours: '24/7', address: '' },
              { id: 2, name: 'Happy Paws Clinic', specialty: 'general', phone: '(555) 010-2020', hours: 'Mon-Sat 9-6', address: '12 Meadow Lane' },
            ],
          });
          toast.info('Using demo data', 'Backend not reachable — showing sample dashboard');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  const recentTranslations = [
    {
      id: 1,
      animal: 'Dog',
      emotion: 'happy',
      translation: 'I want to play fetch!',
      confidence: 0.94,
      language: 'en-IN',
      voice: 'neha',
      created_at: new Date(Date.now() - 300000).toISOString(),
    },
    {
      id: 2,
      animal: 'Cat',
      emotion: 'hungry',
      translation: 'Feeding time, please!',
      confidence: 0.87,
      language: 'hi-IN',
      voice: 'shubh',
      created_at: new Date(Date.now() - 86400000 * 2).toISOString(),
      assisted: true,
    },
    {
      id: 3,
      animal: 'Dog',
      emotion: 'scared',
      translation: 'Thunder is scary, stay with me.',
      confidence: 0.91,
      language: 'en-IN',
      voice: 'neha',
      created_at: new Date(Date.now() - 86400000 * 5).toISOString(),
    },
  ];

  const handlePlayTranslation = (translation) => {
    setNowPlaying(translation.id);
    toast.info('Playing audio', translation.translation);
    setTimeout(() => setNowPlaying(null), 3000);
  };

  const getPetStats = () => {
    if (!data?.pets) return { total: 0, healthy: 0, needsAttention: 0 };
    const total = data.pets.length;
    const needsAttention = (data.due_vaccinations?.length || 0) + (data.due_care_tasks?.length || 0);
    return {
      total,
      healthy: Math.max(0, total - Math.min(needsAttention, total)),
      needsAttention: Math.min(needsAttention, total),
    };
  };

  const petStats = getPetStats();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
        <h2 className="text-xl font-bold text-white">Loading dashboard…</h2>
        <p className="mt-2 text-text-secondary">Fetching your pet data</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="glass-panel rounded-3xl p-8 relative overflow-hidden">
        {/* Decorative background */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -mr-16 -mt-16" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl -mb-16 -ml-16" />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex items-center gap-1 px-2 py-1 rounded bg-white/10">
              <Sparkles className="w-4 h-4 text-primary animate-pulse" />
              <span className="text-xs text-primary font-bold uppercase tracking-tighter">Live</span>
            </div>
            <span className="text-xs text-muted">
              {new Date().toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white mt-2 mb-2">
            Hey there, Pet Parent! 👋
          </h1>
          <p className="text-text-secondary text-lg">
            Everything your pets need at a glance. {petStats.needsAttention > 0 ? `You have {petStats.needsAttention} item{s === 1 ? '' : 's'} needing attention.` : 'All your pets are doing great!'}
          </p>

          {/* Quick Actions */}
          <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <QuickActionCard
              icon={Zap}
              label="Quick Translate"
              description="Record your pet's sound"
              onClick={() => {
                // Navigate to translate page
                window.location.href = '/translate';
              }}
            />
            <QuickActionCard
              icon={PawPrint}
              label="My Pets"
              description="View all pet profiles"
              onClick={() => {
                window.location.href = '/pets';
              }}
            />
            <QuickActionCard
              icon={CalendarClock}
              label="Care Tasks"
              description="Check upcoming tasks"
              onClick={() => {
                setActiveTab('overview');
              }}
            />
            <QuickActionCard
              icon={MapPin}
              label="Find Vet"
              description="Emergency contacts"
              color="red"
              onClick={() => {
                window.location.href = '/vet-directory';
              }}
            />
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={PawPrint}
          label="Total Pets"
          value={data.total_pets}
          subtitle="Active profiles"
          trend={{ positive: true, value: 12 }}
        />
        <StatCard
          icon={HeartPulse}
          label="Healthy"
          value={petStats.healthy}
          subtitle="No active issues"
          trend={{ positive: true, value: 0 }}
        />
        <StatCard
          icon={AlertTriangle}
          label="Needs Attention"
          value={petStats.needsAttention}
          subtitle="Overdue or due soon"
          trend={{ positive: petStats.needsAttention === 0, value: petStats.needsAttention }}
        />
        <StatCard
          icon={Languages}
          label="Translations"
          value="247"
          subtitle="Total this month"
          trend={{ positive: true, value: 18 }}
        />
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left Column: Pets + Quick Actions */}
        <div className="flex flex-col gap-8 lg:flex-col lg:gap-6">
          {/* Pets Overview */}
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <PawPrint className="h-5 w-5 text-primary" />
                <h2 className="font-bold text-white">Your Pets</h2>
              </div>
              <button
                onClick={() => (window.location.href = '/pets')}
                className="text-xs text-primary hover:text-primary/80 hover:underline transition-colors"
              >
                Manage all →
              </button>
            </div>
            <div className="grid gap-3">
              {(data.pets || []).map((pet) => (
                <PetCard key={pet.id} pet={pet} />
              ))}
              {(data.pets || []).length === 0 && (
                <div className="text-center py-8 text-muted">
                  <span className="text-3xl mb-2">🐾</span>
                  <p className="text-sm">No pets yet. Add your first pet!</p>
                  <button
                    onClick={() => (window.location.href = '/pets')}
                    className="mt-3 text-primary hover:text-primary/80 underline text-sm"
                  >
                    Add a pet
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Care Tasks */}
          <AlertCard
            icon={ListChecks}
            title="Upcoming Care Tasks"
            items={(data.due_care_tasks || []).map((t) => ({
              name: t.task,
              status: t.status,
            }))}
            onViewAll={() => (window.location.href = '/care-schedules')}
          />
        </div>

        {/* Middle Column: Health + Vaccinations */}
        <div className="flex flex-col gap-8 lg:flex-col lg:gap-6">
          <AlertCard
            icon={Syringe}
            title="Vaccinations Due"
            items={(data.due_vaccinations || []).map((v) => ({
              name: v.name,
              status: v.status,
              due_on: v.due_on,
              days_overdue: v.days_overdue,
              days_left: v.days_left,
            }))}
            onViewAll={() => (window.location.href = '/health')}
          />

          {/* Recent Translations */}
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Volume2 className="h-5 w-5 text-primary" />
                <h2 className="font-bold text-white">Recent Translations</h2>
              </div>
              <button
                onClick={() => (window.location.href = '/translate')}
                className="text-xs text-primary hover:text-primary/80 hover:underline transition-colors"
              >
                View all →
              </button>
            </div>
            <div className="space-y-3">
              {recentTranslations.map((t) => (
                <RecentTranslationItem
                  key={t.id}
                  translation={t}
                  onPlay={handlePlayTranslation}
                  onClick={() => {
                    // Could open detail modal
                  }}
                />
              ))}
              {recentTranslations.length === 0 && (
                <div className="text-center py-8 text-muted">
                  <span className="text-2xl mb-2">🔊</span>
                  <p className="text-sm">No translations yet. Record your pet's first sound!</p>
                  <button
                    onClick={() => (window.location.href = '/translate')}
                    className="mt-3 text-primary hover:text-primary/80 underline text-sm"
                  >
                    Start translating
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Emergency Vets + Activity */}
        <div className="flex flex-col gap-8 lg:flex-col lg:gap-6">
          <AlertCard
            icon={Phone}
            title="Emergency Vets"
            items={(data.emergency_vets || []).map((vet) => ({
              name: vet.name,
              status: vet.specialty === 'emergency' ? 'emergency' : 'active',
            }))}
            onViewAll={() => (window.location.href = '/vet-directory')}
          />

          {/* Activity Feed */}
          <div className="glass-panel rounded-2xl p-6 flex-1 min-h-[300px]">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                <h2 className="font-bold text-white">Recent Activity</h2>
              </div>
            </div>
            <div className="space-y-4">
              {[
                {
                  icon: Zap,
                  color: 'text-emerald-400',
                  title: 'Translation completed',
                  subtitle: 'Buddy said "I want to play fetch!"',
                  time: '5 min ago',
                },
                {
                  icon: CalendarClock,
                  color: 'text-amber-400',
                  title: 'Care task due',
                  subtitle: "Mia's litter box clean is overdue",
                  time: '2 hours ago',
                },
                {
                  icon: Syringe,
                  color: 'text-red-400',
                  title: 'Vaccination overdue',
                  subtitle: "Buddy's Rabies vaccine is 280 days overdue",
                  time: '1 day ago',
                },
                {
                  icon: PawPrint,
                  color: 'text-cyan-400',
                  title: 'New translation',
                  subtitle: 'Mia said "Feeding time, please!" (Hindi)',
                  time: '3 days ago',
                },
              ].map((activity, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex-shrink-0">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${activity.color}`}>
                      <activity.icon className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white text-sm">{activity.title}</p>
                    <p className="text-xs text-muted">{activity.subtitle}</p>
                    <p className="text-xs text-muted">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
