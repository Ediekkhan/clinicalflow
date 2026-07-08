import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function LabAnalyticsPage() {
  return <EntityDashboard entity="lab" view="analytics" title="Lab Analytics" subtitle="Request volume, turnaround time, critical results, and test category performance." />;
}
