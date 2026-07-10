'use client';

import { Clock, FileText } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { EmptyState } from '@/components/shared/EmptyState';
import { api } from '@/lib/auth';
import type { PatientTicket, QueueStatus } from '@/types';
import { cn } from '@/lib/utils';

const statuses: QueueStatus[] = ['QUEUED', 'BEING_SEEN', 'RESOLVED'];

export function SpecialistPatientKanban({ assignedOnly = false }: { assignedOnly?: boolean }) {
  const [tickets, setTickets] = useState<PatientTicket[]>([]);
  const [selected, setSelected] = useState<PatientTicket | null>(null);
  const [tick, setTick] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function loadTickets() {
      try {
        const endpoint = assignedOnly ? '/api/v1/specialist/patients?assigned_only=true' : '/api/v1/specialist/patients';
        const data = await api.get(endpoint);
        if (!cancelled) setTickets(Array.isArray(data) ? (data as PatientTicket[]) : []);
      } catch (error) {
        console.error(error);
        if (!cancelled) setTickets([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void loadTickets();
    return () => {
      cancelled = true;
    };
  }, [assignedOnly]);

  useEffect(() => {
    const interval = window.setInterval(() => setTick((value) => value + 1), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const grouped = useMemo(
    () => Object.fromEntries(statuses.map((status) => [status, tickets.filter((ticket) => ticket.queue_status === status)])) as Record<QueueStatus, PatientTicket[]>,
    [tickets],
  );

  async function updateStatus(ticketId: string, queue_status: QueueStatus) {
    setTickets((current) => current.map((ticket) => (ticket.id === ticketId ? { ...ticket, queue_status, pendingSync: true } : ticket)));
    setSelected((current) => current && current.id === ticketId ? { ...current, queue_status, pendingSync: true } : current);
    try {
      const updated = await api.patch(`/api/v1/specialist/patients/${ticketId}/status`, { queue_status });
      setTickets((current) => current.map((ticket) => (ticket.id === ticketId ? { ...ticket, ...(updated as PatientTicket), pendingSync: false } : ticket)));
      setSelected((current) => current && current.id === ticketId ? { ...current, ...(updated as PatientTicket), pendingSync: false } : current);
    } catch (error) {
      console.error(error);
    }
  }

  async function escalate(ticketId: string) {
    setTickets((current) => current.map((ticket) => (ticket.id === ticketId ? { ...ticket, urgency_level: 'CRITICAL', is_manually_escalated: true, pendingSync: true } : ticket)));
    setSelected((current) => current && current.id === ticketId ? { ...current, urgency_level: 'CRITICAL', pendingSync: true } : current);
    try {
      const updated = await api.patch(`/api/v1/specialist/patients/${ticketId}/escalate`, {});
      setTickets((current) => current.map((ticket) => (ticket.id === ticketId ? { ...ticket, ...(updated as PatientTicket), pendingSync: false } : ticket)));
      setSelected((current) => current && current.id === ticketId ? { ...current, ...(updated as PatientTicket), pendingSync: false } : current);
    } catch (error) {
      console.error(error);
    }
  }

  if (isLoading) {
    return <div className="grid gap-4 lg:grid-cols-3">{statuses.map((status) => <div key={status} className="h-96 animate-pulse rounded-card bg-slate-100" />)}</div>;
  }

  if (tickets.length === 0) {
    return <EmptyState title="No patients assigned yet" body="Patients will appear here when triage or scheduling assigns them." />;
  }

  return (
    <>
      <div className="grid gap-4 lg:grid-cols-3">
        {statuses.map((status) => (
          <section key={status} className="rounded-card border border-[#E5E7EB] bg-white p-3 shadow-sm">
            <div className="mb-3 px-1">
              <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">{status.replace('_', ' ')}</p>
              <h2 className="font-display text-3xl text-[#111827]">{grouped[status].length}</h2>
            </div>
            <div className="grid gap-3">
              {grouped[status].length === 0 ? <p className="rounded-lg border border-dashed border-[#E5E7EB] p-4 text-center text-sm text-[#6B7280]">No patients</p> : null}
              {grouped[status].map((ticket) => (
                <article key={ticket.id} className={cn('rounded-card border border-[#E5E7EB] bg-[#F7F8FA] p-4', ticket.pendingSync && 'opacity-60')}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono font-bold text-[#111827]">{ticket.ticket_number}</p>
                      <p className="mt-1 text-sm text-[#6B7280]">{[ticket.patient_name, ticket.patient_card_number].filter(Boolean).join(' · ')}</p>
                    </div>
                    <UrgencyBadge level={ticket.urgency_level} />
                  </div>
                  <p className="mt-3 text-sm font-bold text-[#111827]">{ticket.matched_condition_name}</p>
                  <p className="mt-2 inline-flex items-center gap-2 text-sm text-[#6B7280]">
                    <Clock className="h-4 w-4" />
                    {Number(ticket.wait_minutes ?? 0) + tick} min wait
                  </p>
                  {ticket.pendingSync ? <p className="mt-3 rounded-badge bg-[#FFFBEB] px-3 py-1 text-xs font-bold text-[#D97706]">Pending sync</p> : null}
                  <button onClick={() => setSelected(ticket)} className="touch-target mt-4 inline-flex w-full items-center justify-center gap-2 bg-[#2563EB] text-white hover:bg-blue-700">
                    <FileText className="h-4 w-4" />
                    View Details
                  </button>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className={cn('fixed inset-0 z-50 transition', selected ? 'pointer-events-auto bg-black/35' : 'pointer-events-none bg-transparent')}>
        <aside className={cn('absolute right-0 top-0 h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-md transition-transform', selected ? 'translate-x-0' : 'translate-x-full')}>
          {selected ? (
            <div className="grid gap-5">
              <button onClick={() => setSelected(null)} className="touch-target justify-self-end bg-[#F7F8FA] text-[#111827]">Close</button>
              <div>
                <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Patient Details</p>
                <h2 className="font-display text-4xl text-[#111827]">{selected.patient_name}</h2>
                <p className="font-mono text-sm font-bold text-[#2563EB]">{selected.patient_card_number}</p>
              </div>
              <section className="rounded-card bg-[#F7F8FA] p-4">
                <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Symptoms</p>
                <p className="mt-2 text-sm leading-6 text-[#111827]">{selected.symptom_description}</p>
              </section>
              <section className="grid gap-3 rounded-card border border-[#E5E7EB] p-4">
                <UrgencyBadge level={selected.urgency_level} />
                <p className="font-bold text-[#111827]">{selected.matched_condition_name}</p>
                <p className="text-sm text-[#6B7280]">{selected.assigned_specialty}</p>
              </section>
              <div className="grid gap-3 sm:grid-cols-3">
                <button onClick={() => void updateStatus(selected.id, 'BEING_SEEN')} className="front-desk-target bg-[#2563EB] text-white">Mark Being Seen</button>
                <button onClick={() => void updateStatus(selected.id, 'RESOLVED')} className="front-desk-target bg-[#111827] text-white">Mark Resolved</button>
                <button onClick={() => void escalate(selected.id)} className="front-desk-target bg-[#FEF2F2] text-[#DC2626]">Escalate to CRITICAL</button>
              </div>
            </div>
          ) : null}
        </aside>
      </div>
    </>
  );
}
