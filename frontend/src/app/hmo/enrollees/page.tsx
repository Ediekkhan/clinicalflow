import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HmoEnrolleesPage() {
  return <EntityDashboard entity="hmo" view="members" title="Enrollees" subtitle="Search members by name, member ID, phone, plan, high utilization, claims status, and account state." />;
}
