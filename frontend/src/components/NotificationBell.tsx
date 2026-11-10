'use client';

import { Bell, Check, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { useNotifications } from '@/hooks/useNotifications';
import { cn } from '@/lib/utils';
import type { SynNotification } from '@/types';

function notificationEvent(notification: SynNotification) {
  return (notification.event_type ?? notification.type ?? '').replaceAll('.', '_').toUpperCase();
}

function routeForNotification(notification: SynNotification) {
  switch (notificationEvent(notification)) {
    case 'NEW_TICKET':
    case 'QUEUE_UPDATE':
    case 'BEING_SEEN':
    case 'TRIAGE_RESULT':
    case 'PRESCRIPTION_READY':
    case 'LAB_RESULT':
      return '/specialist/patients';
    case 'APPOINTMENT_ASSIGNED':
    case 'APPOINTMENT_CONFIRMED':
    case 'APPOINTMENT_CANCELLED':
    case 'APPOINTMENT_REMINDER':
    case 'APPOINTMENT_RESCHEDULED':
    case 'PATIENT_CHECKED_IN':
      return '/specialist/schedule';
    default:
      return null;
  }
}

export function NotificationBell() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);
  const { notifications, unreadCount, markAllRead, markRead, acknowledge } = useNotifications();
  const visibleNotifications = useMemo(
    () => notifications.filter((item) => !item.is_read || (item.requires_acknowledgement && !item.acknowledged_at)),
    [notifications],
  );

  async function handleOpen(notification: SynNotification) {
    await markRead(notification.id);
    const route = routeForNotification(notification);
    if (route) {
      setOpen(false);
      router.push(route);
    }
  }

  async function handleAcknowledge(notification: SynNotification) {
    setAcknowledgingId(notification.id);
    try {
      await acknowledge(notification.id);
    } finally {
      setAcknowledgingId(null);
    }
  }

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
          <div className="flex items-center justify-between border-b border-[#dbe2dc] p-4">
            <div>
              <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Notifications</p>
              <h2 className="font-display text-3xl text-[#10231e]">{unreadCount} unread</h2>
            </div>
            <button onClick={() => setOpen(false)} className="grid h-12 w-12 place-items-center rounded-lg hover:bg-[#f4f5ef]" aria-label="Close notifications">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="p-4">
            <button onClick={markAllRead} className="touch-target w-full bg-[#0b5d4b] text-white hover:bg-blue-700">Mark All Read</button>
          </div>
          <div className="grid gap-3 overflow-y-auto p-4 pt-0">
            {visibleNotifications.length === 0 ? (
              <div className="rounded-card border border-dashed border-[#dbe2dc] bg-white p-8 text-center text-sm text-[#60706a]">You're all caught up</div>
            ) : (
              visibleNotifications.map((item) => (
                <article key={item.id} className="rounded-card border border-[#dbe2dc] bg-white p-4 text-left shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-bold text-[#10231e]">{item.title}</p>
                      <p className="mt-1 text-sm text-[#60706a]">{item.body}</p>
                    </div>
                    {item.urgency_level ? <UrgencyBadge level={item.urgency_level} /> : null}
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {routeForNotification(item) ? (
                      <button type="button" onClick={() => void handleOpen(item)} className="touch-target border border-[#0b5d4b] px-4 text-sm font-semibold text-[#0b5d4b] hover:bg-[#e9f7f2]">
                        View appointment
                      </button>
                    ) : null}
                    {item.requires_acknowledgement && !item.acknowledged_at ? (
                      <button type="button" disabled={acknowledgingId === item.id} onClick={() => void handleAcknowledge(item)} className="touch-target inline-flex items-center gap-2 bg-[#0b5d4b] px-4 text-sm font-semibold text-white disabled:opacity-60">
                        <Check className="h-4 w-4" />
                        {acknowledgingId === item.id ? 'Acknowledging...' : 'Acknowledge'}
                      </button>
                    ) : null}
                  </div>
                </article>
              ))
            )}
          </div>
        </aside>
      </div>
    </>
  );
}
