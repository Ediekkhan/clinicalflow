import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseQueuePage() {
  return <EntityDashboard entity="nurse" view="queue" title="Triage Queue" subtitle="Clinic-nurse Kanban with vitals, check-in, manual escalation, and queue overtake actions." />;
}
