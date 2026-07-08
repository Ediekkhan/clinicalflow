import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoUtilizationPage() {
  return <EntityDashboard entity="hmo" view="utilization" title="Utilization Analytics" subtitle="Condition categories, monthly spend trend, high-cost enrollees, geography, and plan performance." />;
}
