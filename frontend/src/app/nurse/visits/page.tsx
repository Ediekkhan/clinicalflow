import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NurseVisitsPage() {
  return <EntityDashboard entity="nurse" view="visits" title="My Visits" subtitle="Community-nurse home visit assignments with map actions, timers, and report submission." />;
}
