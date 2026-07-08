import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoDashboardPage() {
  return <EntityDashboard entity="hmo" view="overview" title="HMO Overview" subtitle="Enrollees, utilization, pending authorizations, claims, partner facilities, and payments." />;
}
