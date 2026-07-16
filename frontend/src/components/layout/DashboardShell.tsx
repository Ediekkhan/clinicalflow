'use client';

import Link from 'next/link';

import type { ReactNode } from 'react';
import { LogOut } from 'lucide-react';
import { NotificationBell } from '@/components/layout/NotificationBell';
import { MobileBottomNav, type DashboardNavItem } from '@/components/layout/MobileBottomNav';
import { Sidebar } from '@/components/layout/Sidebar';

type DashboardShellProps = {
  entityType: string;
  navItems: DashboardNavItem[];
  children: ReactNode;
  basePath?: string;
  identity?: {
    name: string;
    subtitle: string;
    badge?: string;
    initials: string;
  };
};

const fallbackIdentity = {
  name: 'ClinicalFlow User',
  subtitle: 'Secure workspace',
  initials: 'SV',
};

export function DashboardShell({
  entityType,
  navItems,
  children,
  basePath,
  identity = fallbackIdentity,
}: DashboardShellProps) {
  const resolvedBase = basePath ?? navItems[0]?.href ?? '/dashboard';

  return (
    <div className="min-h-screen bg-[#f4f5ef] text-[#10231e]">
      <a href="#main-content" className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-lg bg-white px-4 py-3 font-semibold text-blue-700 shadow-lg transition focus:translate-y-0">Skip to main content</a>
      <Sidebar entityType={entityType} basePath={resolvedBase} navItems={navItems} identity={identity} />
      <main id="main-content" tabIndex={-1} className="min-h-screen pb-24 md:ml-[288px] md:pb-0">
        <header className="flex items-center justify-between px-4 py-4 md:hidden">
          <Link href="/logout" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm">
            <LogOut className="h-4 w-4" />
            Logout
          </Link>
          <NotificationBell basePath={resolvedBase} />
        </header>
        <div className="mx-auto w-full max-w-[1320px] px-5 py-8 md:px-10 md:py-10 xl:px-14 xl:py-12">{children}</div>
      </main>
      <MobileBottomNav navItems={navItems} />
    </div>
  );
}
