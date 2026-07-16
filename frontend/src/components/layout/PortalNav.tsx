"use client";

import Link from 'next/link';
import React from 'react';

export type NavItem = { href: string; label: string; icon?: React.ComponentType<any> };

export function PortalNav({ items }: { items: NavItem[] }) {
  return (
    <nav className="flex flex-wrap gap-2">
      {items.map((item) => (
        <Link key={item.href} href={item.href} className="inline-flex min-h-12 items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold text-slate-200 hover:bg-white/10">
          {item.icon ? <item.icon className="h-4 w-4" /> : null}
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export default PortalNav;
