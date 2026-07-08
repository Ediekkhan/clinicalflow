'use client';

import Link from 'next/link';
import { Bell, X } from 'lucide-react';
import { useState } from 'react';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { useNotifications } from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { notifications, unreadCount, markAllRead } = useNotifications();

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="relative grid h-12 w-12 place-items-center rounded-lg text-white hover:bg-white/10"
        aria-label="Open specialist notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount ? <span className="absolute right-2 top-2 h-3 w-3 rounded-full bg-[#DC2626]" /> : null}
      </button>
      <div className={cn('fixed inset-0 z-50 transition', open ? 'pointer-events-auto bg-black/35' : 'pointer-events-none bg-transparent')}>
        <aside className={cn('absolute right-0 top-0 h-full w-full max-w-md bg-white shadow-md transition-transform', open ? 'translate-x-0' : 'translate-x-full')}>
          <div className="flex items-center justify-between border-b border-[#E5E7EB] p-4">
            <div>
              <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Notifications</p>
              <h2 className="font-display text-3xl text-[#111827]">{unreadCount} unread</h2>
            </div>
            <button onClick={() => setOpen(false)} className="grid h-12 w-12 place-items-center rounded-lg hover:bg-[#F7F8FA]" aria-label="Close notifications">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="p-4">
            <button onClick={markAllRead} className="touch-target w-full bg-[#2563EB] text-white hover:bg-blue-700">Mark All Read</button>
          </div>
          <div className="grid gap-3 overflow-y-auto p-4 pt-0">
            {notifications.filter((item) => !item.is_read).map((item) => (
              <article key={item.id} className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-bold text-[#111827]">{item.title}</p>
                    <p className="mt-1 text-sm text-[#6B7280]">{item.body}</p>
                  </div>
                  {item.urgency_level ? <UrgencyBadge level={item.urgency_level} /> : null}
                </div>
                <Link href="/hospital/doctor/patients" className="mt-4 inline-flex min-h-12 items-center text-sm font-bold text-[#2563EB]">
                  View Patient →
                </Link>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </>
  );
}
