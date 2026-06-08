import Link from 'next/link';
import { Activity, CalendarDays, LayoutDashboard, ListChecks } from 'lucide-react';
import { NotificationBell } from '@/components/NotificationBell';
import { demoSpecialist } from '@/lib/syn-data';

const nav = [
  { href: '/specialist/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/specialist/patients', label: 'Patients', icon: Activity },
  { href: '/specialist/schedule', label: 'Schedule', icon: CalendarDays },
  { href: '/specialist/notifications', label: 'Notifications', icon: ListChecks },
];

export function SpecialistShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#F7F8FA] pt-12">
      <header className="bg-[#0D1117] text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 p-4 md:p-6">
          <div>
            <Link href="/specialist/dashboard" className="font-display text-3xl text-emerald-300">SynaptiVerse</Link>
            <p className="text-sm text-slate-300">{demoSpecialist.full_name} · {demoSpecialist.specialty}</p>
          </div>
          <nav className="flex flex-wrap gap-2">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="inline-flex min-h-12 items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold text-slate-200 hover:bg-white/10">
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            ))}
          </nav>
          <NotificationBell />
        </div>
      </header>
      {children}
    </div>
  );
}

