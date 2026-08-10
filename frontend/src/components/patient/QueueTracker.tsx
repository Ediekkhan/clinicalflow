'use client';

import { useEffect, useState } from 'react';
import { Share2, Ticket } from 'lucide-react';
import { Badge } from '@/components/shared/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';

type QueueItem = {
  id?: string;
  ticket_number?: string;
  urgency_level?: 'CRITICAL' | 'URGENT' | 'ROUTINE';
  queue_position?: string | number;
  status?: string;
  queue_status?: string;
  specialist_name?: string;
  provider_name?: string;
  specialty?: string;
  room_label?: string;
  facility_name?: string;
  estimated_wait?: string;
  wait_minutes?: string | number;
};

function tone(level?: string) {
  if (level === 'CRITICAL') return 'critical';
  if (level === 'URGENT') return 'urgent';
  return 'routine';
}

export function QueueTracker() {
  const [queueItem, setQueueItem] = useState<QueueItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadQueue() {
      try {
        const data = await api.get('/api/v1/patient/queue');
        if (!cancelled) setQueueItem((data ?? null) as QueueItem | null);
      } catch (error) {
        console.error(error);
        if (!cancelled) setQueueItem(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadQueue();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isLoading) {
    return <div className="mx-auto h-96 max-w-sm animate-pulse rounded-2xl bg-slate-100" />;
  }

  if (!queueItem) {
    return <EmptyState icon={Ticket} title="No active queue ticket" body="Your queue status will appear here after triage or check-in." />;
  }

  const status = queueItem.queue_status ?? queueItem.status;
  const currentQueue = queueItem;
  const provider = queueItem.specialist_name ?? queueItem.provider_name ?? '';
  const wait = queueItem.estimated_wait ?? (queueItem.wait_minutes ? `${queueItem.wait_minutes} minutes` : '');
  async function sharePosition() {
    const text = `My ClinicalFlow queue position is ${currentQueue.queue_position ?? '—'}${currentQueue.facility_name ? ` at ${currentQueue.facility_name}` : ''}.`;
    if (navigator.share) {
      await navigator.share({ title: 'My queue position', text });
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
    }
  }

  return (
    <section className="mx-auto max-w-sm rounded-2xl border-t-4 border-amber-500 bg-white p-8 text-center shadow-md">
      {queueItem.urgency_level ? <Badge tone={tone(queueItem.urgency_level)}>{queueItem.urgency_level}</Badge> : null}
      {queueItem.ticket_number ? <p className="mt-6 font-mono text-2xl font-bold text-slate-900">{queueItem.ticket_number}</p> : null}
      <p className="mt-7 text-sm text-slate-500">You are</p>
      <p className="font-display text-7xl text-[#0b5d4b]">{queueItem.queue_position ?? '—'}</p>
      <p className="text-sm text-slate-500">in queue</p>
      <div className="my-6 border-t border-slate-100" />
      {provider ? <h3 className="font-semibold text-slate-900">{provider}</h3> : null}
      {[queueItem.specialty, queueItem.room_label].filter(Boolean).length ? <p className="mt-1 text-sm text-slate-500">{[queueItem.specialty, queueItem.room_label].filter(Boolean).join(' - ')}</p> : null}
      {queueItem.facility_name ? <p className="text-xs text-slate-400">{queueItem.facility_name}</p> : null}
      {wait ? <p className="mt-5 text-sm font-semibold text-slate-600">{wait}</p> : null}
      {status ? <div className="mt-5 rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-600">{status}</div> : null}
      <button type="button" onClick={() => void sharePosition()} className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 hover:bg-slate-50">
        <Share2 className="h-4 w-4" />
        Share your position
      </button>
    </section>
  );
}
