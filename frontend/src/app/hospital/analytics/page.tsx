import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function HospitalAnalyticsPage() {
  return <EntityDashboard entity="hospital" view="analytics" title="Hospital Analytics" subtitle="Patients per day, condition mix, average wait time, and specialty utilization." />;
}
