'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { PatientAppointments } from '@/components/patient/PatientAppointments';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientAppointmentsPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Appointments</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Your confirmed care visits</h2>
          <p className="mt-1 text-sm text-slate-500">Upcoming consultations, follow-ups, and lab visits connected to your health card.</p>
        </section>
        <PatientAppointments />
      </div>
    </DashboardShell>
  );
}
