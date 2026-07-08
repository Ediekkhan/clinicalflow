import { EntityDashboard } from '@/components/entity/EntityDashboard';

export default function NursePatientsPage() {
  return <EntityDashboard entity="nurse" view="patients" title="Patients" subtitle="Clinic and community patients assigned for vitals, visits, monitoring, and care plans." />;
}
