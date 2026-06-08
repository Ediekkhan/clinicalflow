'use client';

import { AlertTriangle, Clock, MessageSquareText, Stethoscope } from 'lucide-react';
import { useState } from 'react';
import { PatientContextDrawer } from '@/components/PatientContextDrawer';
import { urgencyMeta, type Ticket, type UrgencyLevel } from '@/lib/types';
import { cn } from '@/lib/utils';

const columns: UrgencyLevel[] = ['CRITICAL', 'URGENT', 'ROUTINE'];

export function TriageKanban({
  grouped,
  forceOvertake,
  setStatus,
}: {
  grouped: Record<UrgencyLevel, Ticket[]>;
  forceOvertake: (ticketId: string) => void;
  setStatus: (ticketId: string, status: 'BEING_SEEN' | 'RESOLVED') => void;
}) {
  const [activeTicket, setActiveTicket] = useState<Ticket | null>(null);

  return (
    <>
      <div className="grid gap-4 lg:grid-cols-3">
        {columns.map((level) => {
          const meta = urgencyMeta[level];
          return (
            <section key={level} className={cn('min-h-[560px] rounded-lg border p-3', meta.fill, meta.border)}>
              <div className="mb-3 flex items-center justify-between px-1">
                <div>
                  <p className="text-sm font-medium uppercase tracking-wider text-slate-500">{meta.label}</p>
                  <h2 className={cn('text-2xl font-bold tracking-tight', meta.text)}>{meta.heading}</h2>
                </div>
                <span className="rounded-lg bg-white px-3 py-2 text-sm font-bold text-slate-900 shadow-sm">
                  {grouped[level].length}
                </span>
              </div>
              <div className="grid gap-3">
                {grouped[level].map((ticket) => (
                  <article
                    key={ticket.id}
                    className={cn(
                      'rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition',
                      ticket.pendingSync && 'opacity-60',
                      ticket.pulse && 'animate-overtake-pulse',
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-mono text-2xl font-bold tracking-tight text-slate-900">{ticket.ticket_number}</p>
                        <p className="mt-1 text-sm text-slate-600">{ticket.assigned_specialty || 'Front Desk Review'}</p>
                      </div>
                      <span className={cn('rounded-lg px-3 py-2 text-sm font-bold', meta.fill, meta.text)}>
                        {ticket.urgency_level}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-2 text-sm text-slate-600">
                      <span className="inline-flex items-center gap-2">
                        <MessageSquareText className="h-4 w-4" />
                        {ticket.channel} · {ticket.customer_phone}
                      </span>
                      <span className="inline-flex items-center gap-2">
                        <Stethoscope className="h-4 w-4" />
                        {ticket.queue_status.replace('_', ' ')}
                      </span>
                      {ticket.pendingSync ? (
                        <span className="inline-flex items-center gap-2 rounded-lg bg-amber-50 px-3 py-2 font-medium text-amber-700">
                          <Clock className="h-4 w-4" />
                          ⏱️ Pending Sync
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-4 grid gap-2">
                      <button
                        type="button"
                        onClick={() => forceOvertake(ticket.id)}
                        className="front-desk-target inline-flex items-center justify-center gap-2 bg-rose-50 text-rose-600 hover:bg-rose-100"
                      >
                        <AlertTriangle className="h-5 w-5" />
                        [ FORCED OVERTAKE ⚠️ ]
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveTicket(ticket)}
                        className="touch-target bg-slate-900 text-white hover:bg-slate-800"
                      >
                        Open context
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <PatientContextDrawer
        ticket={activeTicket}
        open={Boolean(activeTicket)}
        onClose={() => setActiveTicket(null)}
        onSetBeingSeen={(ticketId) => setStatus(ticketId, 'BEING_SEEN')}
        onResolve={(ticketId) => setStatus(ticketId, 'RESOLVED')}
      />
    </>
  );
}

