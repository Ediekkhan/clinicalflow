'use client';

import { AlertTriangle, Bell, CalendarDays } from 'lucide-react';
import { useMemo, useState } from 'react';
import { HospitalShell } from '@/components/HospitalShell';
import { NetworkToast } from '@/components/NetworkToast';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { useNotifications } from '@/hooks/useNotifications';

type Tab = 'All' | 'Unread' | 'Urgent';

export default function HospitalNotificationsClient() {
  const { notifications, networkState, markRead } = useNotifications();
  const [tab, setTab] = useState<Tab>('All');
  const visible = useMemo(() => {
    if (tab === 'Unread') return notifications.filter((item) => !item.is_read);
    if (tab === 'Urgent') return notifications.filter((item) => item.urgency_level === 'CRITICAL' || item.urgency_level === 'URGENT');
    return notifications;
  }, [notifications, tab]);

  return (
    <HospitalShell>
      <NetworkToast mode={networkState} />
      <main className="mx-auto grid max-w-5xl gap-5 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Hospital Notifications</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Clinical updates</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          {(['All', 'Unread', 'Urgent'] as Tab[]).map((item) => (
            <button key={item} onClick={() => setTab(item)} className={`touch-target ${tab === item ? 'bg-[#0D7A5F] text-white' : 'bg-white text-[#111827] ring-1 ring-[#E5E7EB]'}`}>
              {item}
            </button>
          ))}
        </div>
        <div className="grid gap-3">
          {visible.map((item) => {
            const Icon = item.urgency_level === 'CRITICAL' ? AlertTriangle : item.title.includes('Appointment') ? CalendarDays : Bell;
            return (
              <article key={item.id} className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
                <div className="grid gap-3 md:grid-cols-[auto_1fr_auto_auto] md:items-center">
                  <Icon className="h-5 w-5 text-[#0D7A5F]" />
                  <div>
                    <p className="font-bold text-[#111827]">{item.title}</p>
                    <p className="text-sm text-[#6B7280]">{item.body}</p>
                  </div>
                  {item.urgency_level ? <UrgencyBadge level={item.urgency_level} /> : null}
                  <button onClick={() => markRead(item.id)} className="touch-target bg-[#E6F4F0] text-[#0D7A5F]">Mark Read</button>
                </div>
              </article>
            );
          })}
        </div>
      </main>
    </HospitalShell>
  );
}
