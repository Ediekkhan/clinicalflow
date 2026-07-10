'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { HealthCard } from '@/components/patient/HealthCard';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientCardPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-6">
        <section className="rounded-2xl border border-slate-100 bg-white p-5 text-center shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#2563EB]">Digital Health Identity</p>
          <h2 className="font-display mt-1 text-3xl text-slate-900">Your SynaptiVerse card</h2>
          <p className="mx-auto mt-1 max-w-2xl text-sm text-slate-500">Use this card at partner facilities to pull up your profile and visit history securely.</p>
        </section>
        <HealthCard />
      </div>
    </DashboardShell>
  );
}
