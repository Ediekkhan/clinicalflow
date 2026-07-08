import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function ClinicDashboardPage() {
  return <EntityDashboard entity="clinic" view="overview" title="Clinic Overview" subtitle="A focused operating view for patients today, waiting queue, available doctors, and upcoming appointments." />;
}
