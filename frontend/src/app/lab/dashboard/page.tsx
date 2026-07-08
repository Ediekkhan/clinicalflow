import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabDashboardPage() {
  return <EntityDashboard entity="lab" view="overview" title="Laboratory Overview" subtitle="Test referrals, sample collection, results ready, completed tests, and turnaround time." />;
}
