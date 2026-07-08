import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalDepartmentsPage() {
  return <EntityDashboard entity="hospital" view="departments" title="Departments" subtitle="Queue fill level, available doctors, and operational load by department." />;
}
