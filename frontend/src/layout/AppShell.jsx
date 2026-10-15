import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, PawPrint, HeartPulse, CalendarDays, Stethoscope, MessagesSquare, Languages, Crown } from 'lucide-react';
import { ToastProvider } from '../components/Toast';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/pets', label: 'Pets', icon: PawPrint },
  { to: '/health', label: 'Health', icon: HeartPulse },
  { to: '/care-schedules', label: 'Care Schedules', icon: CalendarDays },
  { to: '/vet-directory', label: 'Vet Directory', icon: Stethoscope },
  { to: '/expert', label: 'Pet Care Expert', icon: MessagesSquare },
  { to: '/pricing', label: 'Pricing', icon: Crown },
  { to: '/translate', label: 'Translate', icon: Languages },
];

function AppShell() {
  return (
    <ToastProvider>
      <div className="min-h-screen">
        <aside className="fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-white/10 bg-black/20 backdrop-blur-xl">
          <div className="flex h-16 items-center px-6">
            <span className="gradient-text text-xl font-bold">Pet Care Hub</span>
          </div>
          <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm transition-colors ${
                    isActive ? 'bg-white/10 text-primary' : 'text-text-secondary hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <Icon className="h-5 w-5" />
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="ml-60 min-h-screen">
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  );
}

export default AppShell;
