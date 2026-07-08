import { Clock, DoorOpen, Stethoscope } from 'lucide-react';
import type { PatientTicket } from '@/types';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { cn } from '@/lib/utils';

export function TicketDisplay({ ticket, position }: { ticket: PatientTicket; position: number }) {
  const seeing = ticket.queue_status === 'BEING_SEEN';
  return (
    <section
      className={cn(
        'mx-auto grid max-w-xl gap-5 rounded-card border border-[#E5E7EB] bg-white p-6 text-center shadow-sm',
        seeing && 'animate-overtake-pulse border-blue-300 bg-[#e0f2fe]',
      )}
    >
      <div>
        <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Your Ticket</p>
        <p className="mt-2 font-mono text-4xl font-bold tracking-tight text-[#111827]">{ticket.ticket_number}</p>
      </div>
      <div className="grid gap-2">
        <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Position in Queue</p>
        <div className="mx-auto h-2 w-full max-w-sm overflow-hidden rounded-full bg-slate-100">
          <div className="h-full w-3/5 rounded-full bg-[#2563EB]" />
        </div>
        <p className="font-display text-5xl text-[#111827] md:text-6xl">#{position}</p>
        <p className="text-sm text-[#6B7280]">of 7 ahead of you</p>
      </div>
      <div className="grid gap-3 rounded-card bg-[#F7F8FA] p-4 text-left text-sm text-[#111827]">
        <p className="inline-flex items-center gap-2">
          <Stethoscope className="h-4 w-4 text-[#2563EB]" />
          Specialist: Dr. Udo Okon
        </p>
        <p className="inline-flex items-center gap-2">
          <DoorOpen className="h-4 w-4 text-[#2563EB]" />
          Room 4 · {ticket.assigned_specialty}
        </p>
        <p className="inline-flex items-center gap-2">
          <Clock className="h-4 w-4 text-[#2563EB]" />
          Est. Wait: ~{ticket.wait_minutes} mins
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <UrgencyBadge level={ticket.urgency_level} />
        <span className="rounded-badge bg-[#e0f2fe] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[#2563EB]">
          ● {ticket.queue_status.replace('_', ' ')}
        </span>
      </div>
      {seeing ? (
        <p className="rounded-card bg-[#2563EB] px-4 py-3 text-sm font-bold text-white">
          You're up next! Please proceed to Room 4.
        </p>
      ) : null}
    </section>
  );
}
