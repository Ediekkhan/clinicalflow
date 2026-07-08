'use client';

import Link from 'next/link';
import { Bell, CalendarDays, Home, Menu, MessageCircle, Ticket, UserRound, X } from 'lucide-react';
import { useState } from 'react';
import { demoPatient } from '@/lib/syn-data';
import { cn } from '@/lib/utils';

const nav = [
  { href: '/dashboard', label: 'Home', icon: Home },
  { href: '/chat', label: 'AI Triage', icon: MessageCircle },
  { href: '/appointments', label: 'Appointments', icon: CalendarDays },
  { href: '/queue-status', label: 'Queue', icon: Ticket },
  { href: '/my-card', label: 'My Card', icon: UserRound },
];

export function PatientShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#F7F8FA] pt-12">
      <header className="sticky top-12 z-40 border-b border-[#E5E7EB] bg-white">
        <div className="mx-auto max-w-7xl p-4 md:p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <Link href="/dashboard" className="font-display block truncate text-3xl text-[#2563EB]">
                SynaptiVerse
              </Link>
              <span className="mt-1 inline-flex max-w-full rounded-badge bg-[#e0f2fe] px-3 py-1 font-mono text-xs font-bold text-[#2563EB]">
                <span className="truncate">{demoPatient.card_number}</span>
              </span>
            </div>
            <nav className="hidden items-center gap-2 lg:flex">
              {nav.map((item) => (
                <Link key={item.href} href={item.href} className="inline-flex min-h-12 items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold text-[#6B7280] hover:bg-[#e0f2fe] hover:text-[#2563EB]">
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="flex items-center gap-2">
              <button className="hidden h-12 w-12 place-items-center rounded-lg text-[#111827] hover:bg-[#e0f2fe] sm:grid" aria-label="Notifications">
                <Bell className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setMenuOpen((current) => !current)}
                className="grid h-12 w-12 place-items-center rounded-lg text-[#111827] hover:bg-[#e0f2fe] lg:hidden"
                aria-expanded={menuOpen}
                aria-label="Toggle patient navigation"
              >
                {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
          <nav
            className={cn(
              'grid overflow-hidden transition-[grid-template-rows,opacity] duration-200 lg:hidden',
              menuOpen ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0',
            )}
          >
            <div className="min-h-0">
              <div className="mt-4 grid gap-2 border-t border-[#E5E7EB] pt-4">
                {nav.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className="inline-flex min-h-12 items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-bold text-[#6B7280] hover:bg-[#e0f2fe] hover:text-[#2563EB]"
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
