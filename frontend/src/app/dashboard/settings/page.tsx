'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { PatientSettings } from '@/components/patient/PatientSettings';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientSettingsPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-5">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#0b5d4b]">Settings</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Profile and health details</h2>
          <p className="mt-1 text-sm text-slate-500">Keep your health identity accurate for every partner facility.</p>
        </section>
        <PatientSettings />
      </div>
    </DashboardShell>
  );
}
