import Link from 'next/link';
import { CalendarDays, ChevronRight, MessageCircleHeart, Ticket } from 'lucide-react';
import { NetworkToast } from '@/components/NetworkToast';
import { PatientShell } from '@/components/PatientShell';
import { UrgencyBadge } from '@/components/UrgencyBadge';
import { demoPatient, patientTickets } from '@/lib/syn-data';

const actions = [
  { href: '/chat', title: 'Check My Symptoms', body: 'Describe what you feel in English or Pidgin.', icon: MessageCircleHeart },
  { href: '/appointments', title: 'My Appointments', body: 'View clinic times and specialist assignments.', icon: CalendarDays },
  { href: '/queue-status', title: 'Track My Queue', body: 'See your live ticket position and room.', icon: Ticket },
];

export default function PatientDashboardPage() {
  return (
    <PatientShell>
      <NetworkToast mode="connected" />
      <main className="mx-auto grid max-w-7xl gap-6 p-4 md:p-6">
        <section className="flex flex-wrap items-center justify-between gap-4 rounded-card border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <div>
            <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Good morning, Kaldera</p>
            <h1 className="font-display text-4xl text-[#111827] md:text-5xl">How can we help today?</h1>
          </div>
          <span className="rounded-badge bg-[#E6F4F0] px-4 py-2 font-mono text-sm font-bold text-[#0D7A5F]">{demoPatient.card_number}</span>
        </section>
        <section className="grid gap-4 md:grid-cols-3">
          {actions.map((action) => (
            <Link key={action.href} href={action.href} className="group rounded-card border border-[#E5E7EB] bg-white p-6 shadow-sm transition hover:border-[#0D7A5F]">
              <action.icon className="h-8 w-8 text-[#0D7A5F]" />
              <h2 className="mt-5 text-lg font-bold text-[#111827]">{action.title}</h2>
              <p className="mt-2 min-h-12 text-sm leading-6 text-[#6B7280]">{action.body}</p>
              <span className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-[#0D7A5F]">
                Open
                <ChevronRight className="h-4 w-4 transition group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </section>
        <section className="rounded-card border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Recent Activity</h2>
            <Link href="/queue-status" className="text-sm font-bold text-[#0D7A5F]">View queue</Link>
          </div>
          <div className="overflow-hidden rounded-card border border-[#E5E7EB]">
            {patientTickets.slice(0, 3).map((ticket) => (
              <div key={ticket.id} className="data-row grid gap-3 border-b border-[#E5E7EB] last:border-b-0 md:grid-cols-[1fr_auto_auto]">
                <div>
                  <p className="font-mono font-bold text-[#111827]">{ticket.ticket_number}</p>
                  <p className="text-sm text-[#6B7280]">{ticket.matched_condition_name} · {ticket.assigned_specialty}</p>
                </div>
                <UrgencyBadge level={ticket.urgency_level} />
                <span className="rounded-badge bg-[#F7F8FA] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[#6B7280]">{ticket.queue_status.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </PatientShell>
  );
}
