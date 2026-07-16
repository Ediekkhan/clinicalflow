import { Clock, DoorOpen, Stethoscope } from 'lucide-react';
import type { PatientTicket } from '@/types';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { cn } from '@/lib/utils';

type QueueTicket = PatientTicket & {
  specialist_name?: string;
  room_label?: string;
  queue_size?: number;
};

export function TicketDisplay({ ticket, position }: { ticket: QueueTicket; position: number }) {
  const seeing = ticket.queue_status === 'BEING_SEEN';
  return (
    <section
      className={cn(
        'mx-auto grid max-w-xl gap-5 rounded-card border border-[#dbe2dc] bg-white p-6 text-center shadow-sm',
        seeing && 'animate-overtake-pulse border-blue-300 bg-[#e9f6f1]',
      )}
    >
      <div>
        <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Your Ticket</p>
        <p className="mt-2 font-mono text-4xl font-bold tracking-tight text-[#10231e]">{ticket.ticket_number}</p>
      </div>
      <div className="grid gap-2">
        <p className="text-sm font-bold uppercase tracking-wider text-[#60706a]">Position in Queue</p>
        <div className="mx-auto h-2 w-full max-w-sm overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-[#0b5d4b]" style={{ width: `${Math.max(10, Math.min(100, 100 - position * 10))}%` }} />
        </div>
        <p className="font-display text-5xl text-[#10231e] md:text-6xl">#{position}</p>
      </div>
      <div className="grid gap-3 rounded-card bg-[#f4f5ef] p-4 text-left text-sm text-[#10231e]">
        {ticket.specialist_name ? (
          <p className="inline-flex items-center gap-2">
            <Stethoscope className="h-4 w-4 text-[#0b5d4b]" />
            Specialist: {ticket.specialist_name}
          </p>
        ) : null}
        {[ticket.room_label, ticket.assigned_specialty].filter(Boolean).length ? (
          <p className="inline-flex items-center gap-2">
            <DoorOpen className="h-4 w-4 text-[#0b5d4b]" />
            {[ticket.room_label, ticket.assigned_specialty].filter(Boolean).join(' · ')}
          </p>
        ) : null}
        {ticket.wait_minutes != null ? (
          <p className="inline-flex items-center gap-2">
            <Clock className="h-4 w-4 text-[#0b5d4b]" />
            Est. Wait: {ticket.wait_minutes} mins
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <UrgencyBadge level={ticket.urgency_level} />
        <span className="rounded-badge bg-[#e9f6f1] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[#0b5d4b]">
          {ticket.queue_status.replace('_', ' ')}
        </span>
      </div>
      {seeing ? (
        <p className="rounded-card bg-[#0b5d4b] px-4 py-3 text-sm font-bold text-white">
          You're up! Please proceed to the assigned room.
        </p>
      ) : null}
    </section>
  );
}
