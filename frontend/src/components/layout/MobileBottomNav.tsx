'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { LucideIcon } from 'lucide-react';

export type DashboardNavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

type MobileBottomNavProps = {
  navItems: DashboardNavItem[];
};

export function MobileBottomNav({ navItems }: MobileBottomNavProps) {
  const pathname = usePathname();
  const items = navItems.slice(0, 5);

  return (
    <nav aria-label="Dashboard navigation" className="fixed bottom-0 left-0 z-40 grid w-full grid-cols-5 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] md:hidden">
      {items.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={`flex min-h-16 flex-col items-center justify-center gap-1 px-1 text-[10px] font-semibold ${
              active ? 'text-[#2563EB]' : 'text-slate-400'
            }`}
          >
            <item.icon aria-hidden="true" className="h-5 w-5" />
            <span className="w-full truncate text-center">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
