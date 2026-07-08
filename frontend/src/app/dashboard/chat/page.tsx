'use client';

import { DashboardShell } from '@/components/layout/DashboardShell';
import { TriageChat } from '@/components/patient/TriageChat';
import { dashboardEntities } from '@/lib/dashboard-data';

const entity = dashboardEntities.patient;

export default function PatientChatPage() {
  return (
    <DashboardShell entityType={entity.entityType} navItems={entity.nav} basePath={entity.basePath} identity={entity.identity}>
      <TriageChat />
    </DashboardShell>
  );
}
