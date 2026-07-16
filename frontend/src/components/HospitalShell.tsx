'use client';

import Link from 'next/link';
import { Activity, Bell, CalendarDays, ClipboardList, LayoutDashboard, LogOut, Menu, Settings, Tv, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { NotificationBell } from '@/components/NotificationBell';
import { api } from '@/lib/auth';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { PortalNav } from '@/components/layout/PortalNav';

const nav = [
  { href: '/hospital/dashboard', label: 'Hospital Home', icon: LayoutDashboard },
  { href: '/hospital/doctor/patients', label: 'Assigned to Me', icon: ClipboardList },
  { href: '/hospital/queue', label: 'Live Queue', icon: Activity },
  { href: '/hospital/schedule', label: 'My Schedule', icon: CalendarDays },
  { href: '/hospital/notifications', label: 'Notifications', icon: Bell },
  { href: '/hospital/admin/settings', label: 'Settings', icon: Settings },
  { href: '/hospital/waiting-room', label: 'Waiting Room', icon: Tv },
];

type FacilityProfile = { name?: string; location?: string };
type SpecialistProfile = { full_name?: string; specialty?: string };

export function HospitalShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [facility, setFacility] = useState<FacilityProfile | null>(null);
  const [specialist, setSpecialist] = useState<SpecialistProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadProfiles() {
      try {
        const [facilityData, specialistData] = await Promise.allSettled([
          api.get('/api/v1/hospital/me'),
          api.get('/api/v1/auth/specialist/me'),
        ]);
        if (cancelled) return;
        setFacility(facilityData.status === 'fulfilled' ? (facilityData.value as FacilityProfile) : null);
        setSpecialist(specialistData.status === 'fulfilled' ? (specialistData.value as SpecialistProfile) : null);
      } catch (error) {
        console.error(error);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadProfiles();
    return () => {
      cancelled = true;
    };
  }, []);

  const subtitle = [facility?.location, specialist?.full_name, specialist?.specialty].filter(Boolean).join(' · ');

  return (
    <div className="min-h-screen bg-[#F7F8FA] pt-20">
      <Navbar />
      <div className="bg-[#0D1117] text-white">
        <div className="mx-auto max-w-7xl p-4 md:p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <Link href="/hospital/dashboard" className="font-display block truncate text-3xl text-blue-300">
                {facility?.name ?? 'Hospital workspace'}
              </Link>
              {isLoading ? <div className="mt-2 h-4 w-56 animate-pulse rounded bg-white/10" /> : subtitle ? <p className="mt-1 max-w-[70vw] truncate text-sm text-slate-300 md:max-w-none">{subtitle}</p> : null}
            </div>
            <nav className="hidden items-center gap-2 xl:flex">
              <PortalNav items={nav} />
            </nav>
            <div className="flex items-center gap-2">
              <Link href="/logout" className="hidden min-h-12 items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold text-slate-200 hover:bg-white/10 sm:inline-flex">
                <LogOut className="h-4 w-4" />
                Logout
              </Link>
              <div className="hidden sm:block">
                <NotificationBell />
              </div>
            </div>
          </div>
        </div>
      </div>
      {children}
      <Footer />
    </div>
  );
}
