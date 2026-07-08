import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function PharmacyPrescriptionsPage() {
  return <EntityDashboard entity="pharmacy" view="prescriptions" title="Prescriptions" subtitle="Incoming, in-progress, ready, fulfilled, and cancelled prescription workflows." />;
}
