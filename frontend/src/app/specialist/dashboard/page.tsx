import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function SpecialistDashboardPage() {
  return <EntityDashboard entity="specialist" view="overview" title="Specialist Dashboard" subtitle="Patient, schedule, and queue updates from the API." />;
}
