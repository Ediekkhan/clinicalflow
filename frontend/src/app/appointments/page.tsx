import { CalendarDays, MapPin } from 'lucide-react';
import { PatientShell } from '@/components/PatientShell';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { patientTickets } from '@/lib/syn-data';

export default function PatientAppointmentsPage() {
  return (
    <PatientShell>
      <main className="mx-auto grid max-w-5xl gap-5 p-4 md:p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Appointments</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Your clinic schedule</h1>
        </div>
        <div className="grid gap-4">
          {patientTickets.map((ticket) => (
            <article key={ticket.id} className="rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-lg font-bold text-[#111827]">{ticket.ticket_number}</p>
                  <p className="mt-1 text-sm text-[#6B7280]">{ticket.matched_condition_name}</p>
                </div>
                <UrgencyBadge level={ticket.urgency_level} />
              </div>
              <div className="mt-5 grid gap-3 text-sm text-[#111827] md:grid-cols-3">
                <p className="inline-flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 text-[#0D7A5F]" />
                  {new Intl.DateTimeFormat('en-NG', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(ticket.appointment_slot))}
                </p>
                <p>{ticket.assigned_specialty}</p>
                <p className="inline-flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-[#0D7A5F]" />
                  Uyo Family Clinic
                </p>
              </div>
            </article>
          ))}
        </div>
      </main>
    </PatientShell>
  );
}
