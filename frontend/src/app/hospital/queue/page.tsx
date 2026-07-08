import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalQueuePage() {
  return <EntityDashboard entity="hospital" view="queue" title="Hospital Patient Queue" subtitle="All departments in a single Kanban view with reassignment and escalation controls." />;
}
