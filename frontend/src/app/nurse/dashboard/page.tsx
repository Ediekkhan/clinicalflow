import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseDashboardPage() {
  return <EntityDashboard entity="nurse" view="overview" title="Nurse Overview" subtitle="Queue management, vitals entry, escalations, home visits, and care-plan activity." />;
}
