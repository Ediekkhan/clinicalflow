'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { QueueTracker } from '@/components/patient/QueueTracker';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientQueuePage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 text-center shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Live Queue</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Track your visit in real time</h2>
          <p className="mt-1 text-sm text-slate-500">Your position updates automatically when the hospital queue changes.</p>
        </section>
        <QueueTracker />
      </div>
    </DashboardShell>
  );
}
