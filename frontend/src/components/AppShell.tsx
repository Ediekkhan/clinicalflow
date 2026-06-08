import Link from 'next/link';
import { Activity, CalendarDays, Settings, Tv, UserPlus } from 'lucide-react';

const nav = [
  { href: '/hospital/queue', label: 'Queue', icon: Activity },
  { href: '/hospital/appointments', label: 'Appointments', icon: CalendarDays },
  { href: '/hospital/admin/settings', label: 'Settings', icon: Settings },
  { href: '/hospital/waiting-room', label: 'Waiting Room', icon: Tv },
  { href: '/book', label: 'Book Patient', icon: UserPlus },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 p-4 md:p-6">
          <Link href="/hospital/dashboard" className="text-2xl font-bold tracking-tight text-slate-900">
            SynaptiVerse Hospital
          </Link>
          <nav className="flex flex-wrap items-center gap-2">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
