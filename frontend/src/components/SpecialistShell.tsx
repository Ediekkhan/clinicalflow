'use client';

import Link from 'next/link';
import { Activity, CalendarDays, LayoutDashboard, ListChecks, LogOut } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NotificationBell } from '@/components/NotificationBell';
import { api } from '@/lib/auth';

const nav = [
  { href: '/specialist/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/specialist/patients', label: 'Patients', icon: Activity },
  { href: '/specialist/schedule', label: 'Schedule', icon: CalendarDays },
  { href: '/specialist/notifications', label: 'Notifications', icon: ListChecks },
];

type SpecialistProfile = { full_name?: string; specialty?: string };

export function SpecialistShell({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<SpecialistProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      try {
        const data = await api.get('/api/v1/auth/specialist/me');
        if (!cancelled) setProfile((data ?? null) as SpecialistProfile | null);
      } catch (error) {
        console.error(error);
        if (!cancelled) setProfile(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadProfile();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-[#F7F8FA] pt-12">
      <header className="bg-[#0D1117] text-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 p-4 md:p-6">
          <div>
            <Link href="/specialist/dashboard" className="font-display text-3xl text-blue-300">SynaptiVerse</Link>
            {isLoading ? <div className="mt-2 h-4 w-48 animate-pulse rounded bg-white/10" /> : <p className="text-sm text-slate-300">{[profile?.full_name, profile?.specialty].filter(Boolean).join(' · ')}</p>}
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
