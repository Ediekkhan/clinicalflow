'use client';

import { SpecialistPatientKanban } from '@/components/SpecialistPatientKanban';
import { DashboardShell } from '@/components/layout/DashboardShell';
import { dashboardEntities } from '@/lib/dashboard-data';

export default function SpecialistPatientsPage() {
  const entity = dashboardEntities.specialist;
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <div className="grid gap-6 pt-8">
        <header><h1 className="text-4xl font-black text-slate-950">My Patients</h1><p className="mt-2 text-slate-600">Assign triage tickets, update consultation status, and escalate clinical risk.</p></header>
        <SpecialistPatientKanban />
      </div>
    </DashboardShell>
  );
}
