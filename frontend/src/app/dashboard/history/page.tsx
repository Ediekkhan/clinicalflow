'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { PatientHistory } from '@/components/patient/PatientHistory';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientHistoryPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Health History</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Care timeline</h2>
          <p className="mt-1 text-sm text-slate-500">Every triage session, appointment, prescription, and follow-up in one place.</p>
        </section>
        <PatientHistory />
      </div>
    </DashboardShell>
  );
}
