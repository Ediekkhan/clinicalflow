'use client';

import type { ReactNode } from 'react';
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
        <header className="flex items-center justify-end px-4 py-4 md:hidden">
          <NotificationBell basePath={resolvedBase} />
        </header>
        <div className="mx-auto w-full max-w-[1160px] px-5 py-8 md:px-12 md:py-12">{children}</div>
      </main>
      <MobileBottomNav navItems={navItems} />
    </div>
  );
}
