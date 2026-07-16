'use client';

import Link from 'next/link';
import { LogOut } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import type { DashboardNavItem } from '@/components/layout/MobileBottomNav';

type SidebarProps = {
  entityType: string;
  basePath: string;
  navItems: DashboardNavItem[];
  identity: {
    name: string;
    subtitle: string;
    badge?: string;
    initials: string;
  };
};

export function Sidebar({ entityType, basePath, navItems, identity }: SidebarProps) {
  const pathname = usePathname();
  const accent =
    entityType === 'Pharmacy' || entityType === 'Nurse' || entityType === 'State Ministry of Health'
      ? 'bg-[#2563EB]'
      : entityType === 'Doctor / Specialist' || entityType === 'Clinic'
        ? 'bg-[#2563EB]'
        : entityType === 'Laboratory'
          ? 'bg-[#3b82f6]'
          : entityType === 'HMO / Health Insurance'
            ? 'bg-[#2563EB]'
            : 'bg-[#6157f5]';

  return (
    <aside className="fixed left-0 top-0 z-30 hidden h-screen w-[273px] flex-col border-r border-white/10 bg-[#101729] text-white md:flex">
      <div className="border-b border-white/10 px-6 py-8">
        <Link href={basePath} className="text-[17px] font-extrabold uppercase tracking-[0.16em] text-[#6865ff]">
          SYNAPTIVERSE
        </Link>
        <div className="mt-10">
          <div className="flex items-center gap-3">
            <div className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-extrabold text-white ${accent}`}>
              {identity.initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-extrabold text-white">{identity.name}</p>
              <p className="truncate text-xs font-semibold text-[#6865ff]">{identity.subtitle}</p>
              {identity.badge ? <p className="mt-0.5 truncate font-mono text-xs text-[#6865ff]">{identity.badge}</p> : null}
            </div>
          </div>
        </div>
      </div>
      <nav aria-label="Dashboard navigation" className="flex-1 space-y-2 overflow-y-auto px-3 py-6">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex items-center gap-3 rounded-lg px-4 py-3 text-base font-semibold text-slate-400 transition hover:bg-[#202852] hover:text-white',
                active && 'bg-[#202852] text-[#a9b3ff]',
              )}
            >
              <item.icon aria-hidden="true" className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-white/10 px-3 py-4">
        <Link href="/logout" className="flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold text-slate-400 transition hover:bg-[#202852] hover:text-white">
          <LogOut className="h-4 w-4" />
          Logout
        </Link>
      </div>
    </aside>
  );
}
