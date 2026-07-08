import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalDashboardPage() {
  return <EntityDashboard entity="hospital" view="overview" title="Hospital Overview" subtitle="Multi-department operations, queue load, specialists on duty, and critical escalations." />;
}
