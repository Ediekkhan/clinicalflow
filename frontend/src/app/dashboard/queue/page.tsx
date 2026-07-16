'use client';

import { useEffect, useMemo, useState } from 'react';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { Badge } from '@/components/shared/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { QueueTracker } from '@/components/patient/QueueTracker';
import { dashboardEntities } from '@/lib/dashboard-data';
import { api } from '@/lib/auth';
import { Ticket } from '@/lib/types';
import { Clock3, Ticket as TicketIcon } from 'lucide-react';

const entity = dashboardEntities.patient;

type QueueTicket = Ticket & { pendingSync?: boolean; pulse?: boolean };

function tone(level?: string) {
  if (level === 'CRITICAL') return 'critical';
  if (level === 'URGENT') return 'urgent';
  return 'routine';
}

export default function PatientQueuePage() {
  const [tickets, setTickets] = useState<QueueTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  async function loadTickets() {
    try {
      const data = await api.get('/api/v1/tickets');
      setTickets((data ?? []) as QueueTicket[]);
    } catch (error) {
      console.error(error);
      setTickets([]);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTickets();
    const interval = window.setInterval(() => {
      void loadTickets();
    }, 8000);
    return () => window.clearInterval(interval);
  }, []);

  const grouped = useMemo(() => ({
    CRITICAL: tickets.filter((ticket) => ticket.urgency_level === 'CRITICAL' && ticket.queue_status !== 'RESOLVED'),
    URGENT: tickets.filter((ticket) => ticket.urgency_level === 'URGENT' && ticket.queue_status !== 'RESOLVED'),
    ROUTINE: tickets.filter((ticket) => ticket.urgency_level === 'ROUTINE' && ticket.queue_status !== 'RESOLVED'),
  }), [tickets]);

  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 text-center shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Live Queue</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Track your visit in real time</h2>
          <p className="mt-1 text-sm text-slate-500">Your position updates automatically when the hospital queue changes.</p>
        </section>
        <QueueTracker />
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((item) => <div key={item} className="h-28 animate-pulse rounded-2xl bg-slate-100" />)}
          </div>
        ) : tickets.length === 0 ? (
          <EmptyState icon={TicketIcon} title="No active queue tickets" body="Tickets will show up here once the clinic starts receiving them." />
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {(['CRITICAL', 'URGENT', 'ROUTINE'] as const).map((group) => (
              <section key={group} className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">{group}</h3>
                  <Badge tone={group === 'CRITICAL' ? 'critical' : group === 'URGENT' ? 'urgent' : 'routine'}>{grouped[group].length}</Badge>
                </div>
                <div className="space-y-3">
                  {grouped[group].map((ticket) => (
                    <article key={ticket.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-semibold text-slate-900">{ticket.ticket_number}</p>
                          <p className="mt-1 text-sm text-slate-600">{ticket.customer_phone}</p>
                        </div>
                        <Badge tone={tone(ticket.urgency_level)}>{ticket.urgency_level}</Badge>
                      </div>
                      <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                        <Clock3 className="h-4 w-4" />
                        <span>{new Date(ticket.created_at).toLocaleString()}</span>
                      </div>
                      {ticket.raw_intake_text ? <p className="mt-3 text-sm text-slate-600">{ticket.raw_intake_text}</p> : null}
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
