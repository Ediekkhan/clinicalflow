'use client';

import Link from 'next/link';
import { Bell } from 'lucide-react';
import { useState } from 'react';

type NotificationBellProps = {
  basePath: string;
  count?: number;
  items?: { title: string; body: string; href?: string }[];
};

export function NotificationBell({ basePath, count = 0, items = [] }: NotificationBellProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:border-[#2563EB] hover:text-[#2563EB]"
        aria-label="Open notifications"
      >
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span className="absolute right-1 top-1 grid h-5 min-w-5 place-items-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white">
            {count}
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="absolute right-0 top-12 z-40 w-80 rounded-2xl border border-slate-100 bg-white p-3 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <p className="text-sm font-semibold text-slate-900">Notifications</p>
            <Link href={`${basePath}/notifications`} className="text-xs font-semibold text-[#2563EB]">
              View All
            </Link>
          </div>
          <div className="mt-2 grid gap-1">
            {items.length === 0 ? (
              <p className="rounded-xl px-3 py-5 text-center text-xs leading-5 text-slate-500">You're all caught up</p>
            ) : (
              items.slice(0, 5).map((item) => (
                <Link
                  key={`${item.title}-${item.body}`}
                  href={item.href ?? `${basePath}/notifications`}
                  className="rounded-xl px-3 py-2 transition hover:bg-slate-50"
                >
                  <p className="text-sm font-semibold text-slate-800">{item.title}</p>
                  <p className="mt-0.5 text-xs leading-5 text-slate-500">{item.body}</p>
                </Link>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
