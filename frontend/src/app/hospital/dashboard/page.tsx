import Link from 'next/link';
import { Activity, ArrowRight, CalendarDays, CheckCircle2, ClipboardList, Users } from 'lucide-react';
import { HospitalShell } from '@/components/HospitalShell';
import { NetworkToast } from '@/components/NetworkToast';
import { patientTickets } from '@/lib/syn-data';

const assignedCount = patientTickets.filter((ticket) => ticket.assigned_specialist_id === '40000000-0000-4000-8000-000000000001').length;

export default function HospitalDashboardPage() {
  return (
    <HospitalShell>
      <NetworkToast mode="connected" />
      <main className="mx-auto grid max-w-7xl gap-5 p-4 md:p-6">
        <section className="rounded-card border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-wider text-[#6B7280]">Hospital Workspace</p>
          <h1 className="font-display text-4xl text-[#111827] md:text-5xl">Uyo Family Clinic operations</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#6B7280]">
            This is the hospital account area. Patient/client screens live separately under the patient dashboard, while doctors see assigned patients from inside this workspace.
          </p>
        </section>
        <section className="grid gap-4 md:grid-cols-4">
          {[
            { label: 'Assigned to Me', value: assignedCount, icon: ClipboardList },
            { label: 'Patients Waiting', value: patientTickets.filter((ticket) => ticket.queue_status === 'QUEUED').length, icon: Users },
            { label: 'Today’s Appointments', value: patientTickets.length, icon: CalendarDays },
            { label: 'Resolved Today', value: patientTickets.filter((ticket) => ticket.queue_status === 'RESOLVED').length, icon: CheckCircle2 },
          ].map((stat) => (
            <article key={stat.label} className="rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm">
              <stat.icon className="h-6 w-6 text-[#0D7A5F]" />
              <p className="mt-4 text-sm font-bold uppercase tracking-wider text-[#6B7280]">{stat.label}</p>
              <p className="font-display mt-2 text-4xl text-[#111827] md:text-5xl">{stat.value}</p>
            </article>
          ))}
        </section>
        <section className="grid gap-4 md:grid-cols-3">
          {[
            { href: '/hospital/doctor/patients', label: 'Open assigned patients', icon: ClipboardList },
            { href: '/hospital/queue', label: 'Open live hospital queue', icon: Activity },
            { href: '/hospital/schedule', label: 'Open doctor schedule', icon: CalendarDays },
          ].map((action) => (
            <Link key={action.href} href={action.href} className="group rounded-card border border-[#E5E7EB] bg-white p-5 shadow-sm hover:border-[#0D7A5F]">
              <action.icon className="h-6 w-6 text-[#0D7A5F]" />
              <p className="mt-4 font-bold text-[#111827]">{action.label}</p>
              <span className="mt-4 inline-flex min-h-12 items-center gap-2 text-sm font-bold text-[#0D7A5F]">
                Continue <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
              </span>
            </Link>
          ))}
        </section>
      </main>
    </HospitalShell>
  );
}
