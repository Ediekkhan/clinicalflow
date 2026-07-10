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
  name: 'SynaptiVerse User',
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
    <div className="min-h-screen bg-[#f6f8fb]">
      <Sidebar entityType={entityType} basePath={resolvedBase} navItems={navItems} identity={identity} />
      <main className="min-h-screen pb-24 md:ml-[273px] md:pb-0">
        <header className="flex items-center justify-between px-4 py-4 md:hidden">
          <Link href="/logout" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 shadow-sm">
            <LogOut className="h-4 w-4" />
            Logout
          </Link>
          <NotificationBell basePath={resolvedBase} />
        </header>
        <div className="mx-auto w-full max-w-[1160px] px-5 py-8 md:px-12 md:py-12">{children}</div>
      </main>
      <MobileBottomNav navItems={navItems} />
    </div>
  );
}
