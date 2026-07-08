import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicQueuePage() {
  return <EntityDashboard entity="clinic" view="queue" title="Clinic Patient Queue" subtitle="Single-department Kanban for check-ins, consultations, vitals, and resolved visits." />;
}
