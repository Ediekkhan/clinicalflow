'use client';

import Link from 'next/link';
import { Clock3, RefreshCw, Smartphone, Ticket as TicketIcon, Users } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/shared/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';
import type { Ticket } from '@/lib/types';

type QueueStatus = { ticket_number?: string | null; queue_position?: number | null; queue_status?: string };

function urgencyTone(level: Ticket['urgency_level']) {
  return level === 'CRITICAL' ? 'critical' : level === 'URGENT' ? 'urgent' : 'routine';
}

export default function MyVisitPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [queue, setQueue] = useState<QueueStatus | null>(null);
  const [selectedId, setSelectedId] = useState<string>('');
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const [ticketData, queueData] = await Promise.all([
        api.get('/api/v1/tickets'),
        api.get('/api/v1/patient/queue'),
      ]);
      const loaded = (ticketData ?? []) as Ticket[];
      setTickets(loaded);
      setQueue((queueData ?? null) as QueueStatus | null);
      setSelectedId((current) => loaded.some((ticket) => ticket.id === current) ? current : loaded[0]?.id ?? '');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 8000);
    return () => window.clearInterval(timer);
  }, []);

  const selected = useMemo(() => tickets.find((ticket) => ticket.id === selectedId) ?? tickets[0], [selectedId, tickets]);
  const selectedPosition = selected?.ticket_number === queue?.ticket_number ? queue?.queue_position : null;

  return (
    <main className="min-h-screen bg-slate-50 p-4 md:p-6">
      <div className="mx-auto grid max-w-3xl gap-5">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-wider text-blue-600">Live Visit</p>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">My clinic ticket</h1>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => void refresh()} className="touch-target inline-flex items-center gap-2 border border-slate-200 bg-white text-slate-700">
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            <Link href="/dashboard" className="touch-target bg-slate-900 text-white">Dashboard</Link>
          </div>
        </header>

        {tickets.length > 1 ? (
          <section className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-sm font-bold text-blue-800"><Users className="h-5 w-5" /> Shared phone group</div>
            <p className="mt-1 text-sm text-blue-700">Choose the family member ticket you want to track.</p>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
              {tickets.map((ticket, index) => (
                <button key={ticket.id} type="button" onClick={() => setSelectedId(ticket.id)} className={`min-w-40 rounded-lg px-4 py-3 text-left text-sm font-bold ${selected?.id === ticket.id ? 'bg-blue-600 text-white' : 'border border-blue-200 bg-white text-blue-800'}`}>
                  Patient {index + 1}<span className="mt-1 block font-mono text-xs">{ticket.ticket_number}</span>
                </button>
              ))}
            </div>
          </section>
        ) : null}

        {loading ? (
          <div className="h-[480px] animate-pulse rounded-2xl bg-white" />
        ) : !selected ? (
          <EmptyState icon={TicketIcon} title="No visit ticket yet" body="Create a booking or complete triage and your live ticket will appear here." />
        ) : (
          <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
            <div className="bg-slate-950 px-6 py-7 text-center text-white">
              <p className="text-xs font-bold uppercase tracking-[0.25em] text-blue-300">SynaptiVerse Clinic</p>
              <p className="mt-4 font-mono text-3xl font-black tracking-tight sm:text-5xl">{selected.ticket_number}</p>
            </div>
            <div className="grid gap-6 p-6 text-center sm:p-8">
              <Badge tone={urgencyTone(selected.urgency_level)}>{selected.urgency_level}</Badge>
              {selectedPosition != null ? (
                <div>
                  <p className="text-sm font-bold uppercase tracking-wider text-slate-500">You are</p>
                  <p className="font-display text-8xl text-blue-600">#{selectedPosition}</p>
                  <p className="text-lg font-semibold text-slate-700">in line for {selected.assigned_specialty || 'front desk review'}</p>
                </div>
              ) : (
                <div className="rounded-xl bg-slate-50 p-5">
                  <p className="text-sm font-bold uppercase tracking-wider text-slate-500">Visit status</p>
                  <p className="mt-2 text-2xl font-black text-slate-900">{selected.queue_status.replace('_', ' ')}</p>
                </div>
              )}
              <div className="grid gap-3 border-t border-dashed border-slate-300 pt-6 text-left text-sm text-slate-600 sm:grid-cols-2">
                <p className="inline-flex items-center gap-2"><Smartphone className="h-4 w-4 text-blue-600" /> {selected.channel} · {selected.customer_phone}</p>
                <p className="inline-flex items-center gap-2"><Clock3 className="h-4 w-4 text-blue-600" /> Created {new Date(selected.created_at).toLocaleString()}</p>
              </div>
              <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">Keep this screen open. Your position refreshes automatically every eight seconds.</p>
            </div>
          </article>
        )}
      </div>
    </main>
  );
}
