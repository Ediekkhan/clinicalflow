import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function SpecialistPatientsPage() {
  return <EntityDashboard entity="specialist" view="queue" title="My Patients" subtitle="Drag-ready patient cards grouped by queued, being seen, and resolved status." />;
}
